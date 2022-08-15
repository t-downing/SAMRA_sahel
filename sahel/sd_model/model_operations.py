import numpy as np
import pandas as pd
from BPTK_Py import Model, bptk
from BPTK_Py import sd_functions as sd
from ..models import Element, SimulatedDataPoint, MeasuredDataPoint, ConstantValue, ResponseOption, \
    SeasonalInputDataPoint, ForecastedDataPoint, HouseholdConstantValue, ScenarioConstantValue
from datetime import datetime, date
import time, functools
from django.conf import settings
from sqlalchemy import create_engine
from django.db.models import Q


def run_model(scenario_pk: int = 1, responseoption_pk: int = 1):
    start = time.time()
    startdate, enddate = date(2022, 8, 1), date(2024, 8, 1)

    model = Model(starttime=startdate.toordinal(), stoptime=enddate.toordinal(), dt=2)
    zero_flow = model.flow("Zero Flow")
    zero_flow.equation = 0.0

    elements = Element.objects.filter(
        Q(sd_type="Variable", equation__isnull=False) |
        Q(sd_type="Flow", equation__isnull=False) |
        Q(sd_type="Stock") |
        Q(sd_type="Input") |
        Q(sd_type="Seasonal Input") |
        Q(sd_type="Scenario Constant") |
        Q(sd_type="Constant") |
        Q(sd_type="Pulse Input") |
        Q(sd_type="Household Constant")
    )

    model_output_pks = [str(element.pk) for element in elements]
    stop = time.time()
    print(f"init took {stop - start} s")
    start = time.time()

    # initialise all elements and set constants
    for element in elements:
        # so so sorry for using exec, this is the way life must be for now
        if element.sd_type in ["Variable", "Input", "Seasonal Input"]:
            exec(f'_E{element.pk}_ = model.converter("{element.pk}")')
        elif element.sd_type == "Flow":
            exec(f'_E{element.pk}_ = model.flow("{element.pk}")')
        elif element.sd_type == "Stock":
            exec(f'_E{element.pk}_ = model.stock("{element.pk}")')
        elif element.sd_type in ["Constant", "Household Constant", "Scenario Constant"]:
            exec(f'_E{element.pk}_ = model.constant("{element.pk}")')
            print(f"created {element}")
            model.constant(str(element.pk)).equation = element.constant_default_value
        elif element.sd_type == "Pulse Input":
            print(f"trying to set up pulse {element}")
            exec(f'_E{element.pk}_ = model.converter("{element.pk}")')
            pulsevalues = element.pulsevalues.filter(responseoption_id=responseoption_pk)
            if pulsevalues is None:
                continue
            model.converter(str(element.pk)).equation = 0.0
            for pulsevalue in pulsevalues:
                pulse_start_ord = (pulsevalue.startdate - pd.DateOffset(days=15)).toordinal()
                pulse_stop_ord = (pulsevalue.startdate + pd.DateOffset(days=15)).toordinal()
                print(f"start {pulse_start_ord}, stop {pulse_stop_ord}")
                model.converter(str(element.pk)).equation += sd.If(
                    sd.And(sd.time() > pulse_start_ord, sd.time() < pulse_stop_ord), pulsevalue.value, 0.0)
                print(f"set {element} equation to {model.converter(str(element.pk)).equation}")
    stop = time.time()
    print(f"set up elements took {stop - start} s")
    start = time.time()

    # set equations for modeling elements
    all_equations = ""
    smoothed_elements = []
    for element in elements:
        # used it once, might as well use it again
        if element.sd_type in ["Variable", "Flow"]:
            if "smooth" in element.equation:
                # set equation to zero, return to it later to set it properly once everthing else has been set
                print(f"setting {element} equation to zero for now, because it is smoothed")
                all_equations += element.equation
                exec(f'_E{element.pk}_.equation = 0.0')
                smoothed_elements.append(element)
                continue
            try:
                exec(f'_E{element.pk}_.equation = {element.equation}')
                all_equations += element.equation
            except NameError as error:
                print(f"'{element}' equation could not be defined because {error}. "
                      f"Setting equation to 0.0 instead.")
                exec(f'_E{element.pk}_.equation = 0.0')
            except SyntaxError as error:
                print(f"{element} equation is blank, setting to None")

        elif element.sd_type == "Stock":
            model.stock(str(element.pk)).equation = zero_flow
            exec(f'model.stock(str({element.pk})).initial_value = {element.equation}')
            for inflow in element.inflows.filter(equation__isnull=False).exclude(equation=""):
                print(f"adding flow {inflow}")
                model.stock(str(element.pk)).equation += model.flow(inflow.pk) / 30.437 if "mois" in inflow.unit else 1.0
            for outflow in element.outflows.filter(equation__isnull=False).exclude(equation=""):
                print(outflow)
                if "mois" in outflow.unit:
                    model.stock(str(element.pk)).equation -= model.flow(outflow.pk) / 30.437
                else:
                    model.stock(str(element.pk)).equation -= model.flow(outflow.pk)

    stop = time.time()
    print(f"set up equations took {stop - start} s")
    start = time.time()

    # set inputs
    for element in elements:
        if element.sd_type in ["Input", "Seasonal Input"]:
            if f"_E{element.pk}_" in all_equations:
                if element.sd_type == "Input":
                    # load measured points
                    df_m = pd.DataFrame(MeasuredDataPoint.objects.filter(element=element).values())
                    df_m = df_m.groupby("date").mean().reset_index()[["date", "value"]]
                    # load forecasted points
                    df_f = pd.DataFrame(element.forecasteddatapoints.all().values())
                    df_f = df_f.groupby("date").mean().reset_index()[["date", "value"]]
                    if element.pk == 48:
                        print(df_m["date"].max())
                    df = pd.concat([df_m, df_f], ignore_index=True)
                    df["t"] = df["date"].apply(datetime.toordinal)
                    model.points[str(element.pk)] = df[["t", "value"]].values.tolist()
                    model.converter(str(element.pk)).equation = sd.lookup(sd.time(), str(element.pk))
                else:
                    df = pd.DataFrame(SeasonalInputDataPoint.objects.filter(element=element).values())
                    if df.empty:
                        model.converter(str(element.pk)).equation = 1.0
                        print(f"couldn't find seasonal values for {element}, setting eq to 1.0")
                        continue
                    df["date"] = pd.to_datetime(df["date"])
                    df["month"] = df["date"].dt.month
                    df["day"] = df["date"].dt.day
                    df = df.drop(columns=["date", "element_id", "id"])
                    for yearnum in range(startdate.year - 1, enddate.year + 2):
                        df[f"year_{yearnum}"] = yearnum
                    df = pd.melt(df, id_vars=["value", "month", "day"], value_name="year")
                    df["date"] = df.apply(lambda row : date(row["year"], row["month"], row["day"]), axis=1)

                df["t"] = df["date"].apply(datetime.toordinal)
                model.points[str(element.pk)] = df[["t", "value"]].values.tolist()
                model.converter(str(element.pk)).equation = sd.lookup(sd.time(), str(element.pk))
            else:
                model_output_pks.remove(str(element.pk))

    stop = time.time()
    print(f"set up inputs took {stop - start} s")
    start = time.time()

    # smoothed variables
    for element in smoothed_elements:
        print(f"setting smoothed equation for {element} now")
        exec(f'_E{element.pk}_.equation = {element.equation}')

    stop = time.time()
    print(f"set up smoothed variables took {stop - start} s")
    start = time.time()

    # set constant values
    constants_values = {}
    for element in elements:
        if element.sd_type == "Constant":
            try:
                constants_values[str(element.pk)] = element.constantvalues.get(responseoption_id=responseoption_pk).value
            except ConstantValue.DoesNotExist:
                pass
        elif element.sd_type == "Scenario Constant":
            try:
                constants_values[str(element.pk)] = element.scenarioconstantvalues.get(scenario_id=scenario_pk).value
            except ScenarioConstantValue.DoesNotExist:
                pass
        elif element.sd_type == "Household Constant":
            try:
                constants_values[str(element.pk)] = element.householdconstantvalues.get().value
            except HouseholdConstantValue.DoesNotExist:
                pass

    # setup to run model
    model_env = bptk()
    model_env.register_model(model)
    scenario_manager = {"scenario_manager": {"model": model}}
    model_env.register_scenario_manager(scenario_manager)
    # run model
    # for purposes of running bptk, just set scenario to "base"
    bptk_scenario = "base"
    model_env.register_scenarios(scenarios={bptk_scenario: {"constants": constants_values}}, scenario_manager="scenario_manager")
    df = model_env.plot_scenarios(scenarios=bptk_scenario, scenario_managers="scenario_manager", equations=model_output_pks, return_df=True).reset_index()

    stop = time.time()
    print(f"run model took {stop - start} s")
    start = time.time()

    df["date"] = df["t"].apply(datetime.fromordinal)
    df = pd.melt(df, id_vars=["date"], value_vars=model_output_pks)
    # df = df.groupby(["variable", pd.Grouper(key="date", freq="W-MON")]).mean().reset_index()

    stop = time.time()
    print(f"format results took {stop - start} s")
    start = time.time()

    simulationdatapoint_list = [
        SimulatedDataPoint(
            element_id=row.variable,
            value=row.value,
            date=row.date,
            scenario_id=scenario_pk,
            responseoption_id=responseoption_pk
        )
        for row in df.itertuples()
    ]

    stop = time.time()
    print(f"df iterrows took {stop - start} s")
    start = time.time()

    SimulatedDataPoint.objects.filter(scenario_id=scenario_pk, responseoption_id=responseoption_pk).delete()
    SimulatedDataPoint.objects.bulk_create(simulationdatapoint_list)

    stop = time.time()
    print(f"delete and save took {stop - start} s")

    # database_name = settings.DATABASES['default']['NAME']
    # database_url = 'sqlite:///{database_name}'.format(database_name=database_name)
    # engine = create_engine(database_url, echo=False)
    # print(df)
    # df.to_sql("simulateddatapoint", con=engine, if_exists='append')

    return df


def smooth(model, input_var, time_constant, initial_value=None):
    """ Smooth a variable
    (Built-in sd.smooth function does not work properly)
    """
    smoothed_value = model.stock(f"{input_var.name} SMOOTHED")
    if initial_value is None:
        print(f"input_var is {input_var}")
        print(f"input_var name is {input_var.name}")
        initial_value = model.evaluate_equation(input_var.name, model.starttime)
    print(f"setting {input_var} initial value to {initial_value}")
    smoothed_value.initial_value = initial_value
    value_increase = model.flow(f"{input_var.name} SMOOTHING UP")
    value_decrease = model.flow(f"{input_var.name} SMOOTHING DOWN")
    smoothed_value.equation = value_increase - value_decrease
    value_increase.equation = (input_var - smoothed_value) / time_constant
    value_decrease.equation = (smoothed_value - input_var) / time_constant
    return smoothed_value


def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.time()
        value = func(*args, **kwargs)
        run_time = time.time() - start_time
        print(f"Function {func.__name__!r} took {run_time:.4f} s")
        return value
    return wrapper_timer
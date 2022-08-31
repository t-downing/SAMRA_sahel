import numpy as np
import pandas as pd
from BPTK_Py import Model, bptk
from BPTK_Py import sd_functions as sd
from ..models import Element, SimulatedDataPoint, MeasuredDataPoint, ConstantValue, ResponseOption, \
    SeasonalInputDataPoint, ForecastedDataPoint, HouseholdConstantValue, ScenarioConstantValue
from datetime import datetime, date
import time, functools, warnings
from django.conf import settings
from sqlalchemy import create_engine
from django.db.models import Q
from django.db import connection
from contextlib import closing


def run_model(scenario_pk: int = 1, responseoption_pk: int = 1):
    start = time.time()
    startdate, enddate = date(2022, 7, 1), date(2024, 7, 1)

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

    model_output_pks = []
    for element in elements:
        if element.sd_type in ["Variable",  "Stock", "Flow"] and element.model_output_variable:
            model_output_pks.append(str(element.pk))

    # initialise all elements and set constants
    for element in elements:
        if element.sd_type in ["Variable", "Input", "Seasonal Input"]:
            exec(f'_E{element.pk}_ = model.converter("{element.pk}")')
        elif element.sd_type == "Flow":
            exec(f'_E{element.pk}_ = model.flow("{element.pk}")')
        elif element.sd_type == "Stock":
            exec(f'_E{element.pk}_ = model.stock("{element.pk}")')
        elif element.sd_type in ["Constant", "Household Constant", "Scenario Constant"]:
            exec(f'_E{element.pk}_ = model.constant("{element.pk}")')
            model.constant(str(element.pk)).equation = element.constant_default_value
        elif element.sd_type == "Pulse Input":
            exec(f'_E{element.pk}_ = model.converter("{element.pk}")')
            pulsevalues = element.pulsevalues.filter(responseoption_id=responseoption_pk)
            if pulsevalues is None:
                continue
            model.converter(str(element.pk)).equation = 0.0
            for pulsevalue in pulsevalues:
                pulse_start_ord = (pulsevalue.startdate - pd.DateOffset(days=15)).toordinal()
                pulse_stop_ord = (pulsevalue.startdate + pd.DateOffset(days=15)).toordinal()
                model.converter(str(element.pk)).equation += sd.If(
                    sd.And(sd.time() > pulse_start_ord, sd.time() < pulse_stop_ord), pulsevalue.value, 0.0)
    stop = time.time()
    print(f"set up elements took {stop - start} s")
    start = time.time()

    # set equations for modeling elements
    all_equations = ""
    smoothed_elements = []
    for element in elements:
        if element.sd_type in ["Variable", "Flow"]:
            if "smooth" in element.equation:
                # set equation to zero, return to it later to set it properly once everthing else has been set
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
                model.stock(str(element.pk)).equation += model.flow(inflow.pk) / 30.437 if "mois" in inflow.unit else 1.0
            for outflow in element.outflows.filter(equation__isnull=False).exclude(equation=""):
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
                if str(element.pk) in model_output_pks: model_output_pks.remove(str(element.pk))

    stop = time.time()
    print(f"set up inputs took {stop - start} s")
    start = time.time()

    # smoothed variables
    for element in smoothed_elements:
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
    # ignore pandas PerformanceWarnings since bptk will always throw these up if given enough variables to output
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=pd.errors.PerformanceWarning)
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

    # delete and save done with raw SQL delete and insert (twice as fast as built-in bulk_create)
    insert_stmt = (
        "INSERT INTO sahel_simulateddatapoint (element_id, value, date, scenario_id, responseoption_id) "
        f"VALUES {', '.join(['(%s, %s, %s, %s, %s)'] * len(df))}"
    )
    delete_stmt = (
        f"DELETE FROM sahel_simulateddatapoint WHERE "
        f"scenario_id = {scenario_pk} AND responseoption_id = {responseoption_pk}"
    )

    data = []

    for row in df.itertuples():
        data.extend([row.variable, row.value, row.date, scenario_pk, responseoption_pk])

    print(f"SQL iterrows took {time.time() - start} s")
    start = time.time()

    with closing(connection.cursor()) as cursor:
        cursor.execute(delete_stmt)
        cursor.execute(insert_stmt, data)

    print(f"SQL bulk delete and insert took {time.time() - start} s")
    start = time.time()

    return df


def smooth(model, input_var, time_constant, initial_value=None):
    """ Smooth a variable
    (Built-in sd.smooth function does not work properly)
    """
    smoothed_value = model.stock(f"{input_var.name} SMOOTHED")
    if initial_value is None:
        initial_value = model.evaluate_equation(input_var.name, model.starttime)
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


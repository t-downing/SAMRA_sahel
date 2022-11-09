import numpy as np
import pandas as pd
from BPTK_Py import Model, bptk
from BPTK_Py import sd_functions as sd
from ..models import Variable, SimulatedDataPoint, MeasuredDataPoint, ConstantValue, ResponseOption, \
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

    elements = Variable.objects.filter(
        Q(sd_type="Variable", equation__isnull=False) |
        Q(sd_type="Flow", equation__isnull=False) |
        Q(sd_type="Stock", stock_initial_value__isnull=False) |
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
        if element.sd_type in ["Variable", "Stock", "Flow"] and element.model_output_variable:
            model_output_pks.append(str(element.pk))

    # initialise all elements and set constants
    model_locals = {"model": model}
    for element in elements:
        pk = str(element.pk)
        if element.sd_type in ["Variable", "Input", "Seasonal Input"]:
            model_locals.update({f'_E{pk}_': model.converter(pk)})
        elif element.sd_type == "Flow":
            model_locals.update({f'_E{element.pk}_': model.flow(pk)})
        elif element.sd_type == "Stock":
            model_locals.update({f'_E{element.pk}_': model.stock(pk)})
        elif element.sd_type in ["Constant", "Household Constant", "Scenario Constant"]:
            model_locals.update({f'_E{element.pk}_': model.constant(pk)})
            model.constant(pk).equation = element.constant_default_value
        elif element.sd_type == "Pulse Input":
            model_locals.update({f'_E{element.pk}_': model.converter(pk)})
            pulsevalues = element.pulsevalues.filter(responseoption_id=responseoption_pk)
            if pulsevalues is None:
                continue
            model.converter(pk).equation = 0.0
            for pulsevalue in pulsevalues:
                pulse_start_ord = (pulsevalue.startdate - pd.DateOffset(days=15)).toordinal()
                pulse_stop_ord = (pulsevalue.startdate + pd.DateOffset(days=15)).toordinal()
                model.converter(pk).equation += sd.If(
                    sd.And(sd.time() > pulse_start_ord, sd.time() < pulse_stop_ord), pulsevalue.value, 0.0)
    stop = time.time()
    print(f"set up elements took {stop - start} s")
    start = time.time()

    # set equations for modeling elements
    all_equations = ""
    smoothed_elements = []
    for element in elements:
        pk = str(element.pk)
        if element.sd_type in ["Variable", "Flow"]:
            if "smooth" in element.equation:
                # set equation to zero, return to it later to set it properly once everthing else has been set
                all_equations += element.equation
                model.converter(pk).equation = 0.0
                smoothed_elements.append(element)
                continue
            try:
                # exec is limited to use sd.* and smooth functions, and can only see and edit the dict model_locals
                exec(f"temp_eq = {element.equation}", {"__builtins__": None, "sd": sd, "smooth": smooth}, model_locals)
                if element.sd_type == "Variable":
                    model.converter(pk).equation = model_locals.get("temp_eq")
                else:
                    model.flow(pk).equation = model_locals.get("temp_eq")
                all_equations += element.equation
            except NameError as error:
                print(f"'{element}' equation could not be defined because {error}. "
                      f"Setting equation to 0.0 instead.")
                model.converter(pk).equation = 0.0
            except SyntaxError as error:
                print(f"{element} equation is blank, setting to None")

        elif element.sd_type == "Stock":
            print(f"stock for {element}")
            model.stock(pk).equation = zero_flow
            model.stock(pk).initial_value = element.stock_initial_value
            for inflow in element.inflows.filter(equation__isnull=False).exclude(equation=""):
                model.stock(pk).equation += model.flow(inflow.pk) / 30.437 if "mois" in inflow.unit else 1.0
            for outflow in element.outflows.filter(equation__isnull=False).exclude(equation=""):
                if "mois" in outflow.unit:
                    model.stock(pk).equation -= model.flow(outflow.pk) / 30.437
                else:
                    model.stock(pk).equation -= model.flow(outflow.pk)

    stop = time.time()
    print(f"set up equations took {stop - start} s")
    start = time.time()

    # set inputs
    df_m_all = pd.DataFrame(MeasuredDataPoint.objects.filter(date__gte=startdate, date__lte=enddate).values())
    df_f_all = pd.DataFrame(ForecastedDataPoint.objects.filter(date__gte=startdate, date__lte=enddate).values())

    m_time = 0.0
    f_time = 0.0

    for element in elements:
        pk = str(element.pk)
        if element.sd_type in ["Input", "Seasonal Input"]:
            if f"_E{element.pk}_" in all_equations:
                if element.sd_type == "Input":
                    # load measured points
                    m_start = time.time()
                    # df_m = pd.DataFrame(MeasuredDataPoint.objects.filter(element=element).values())
                    # df_m = pd.DataFrame(measureddatapoints.filter(element_id=pk))
                    df_m = df_m_all[df_m_all["element_id"] == int(pk)]
                    if not df_m.empty:
                        df_m = df_m.groupby("date").mean().reset_index()[["date", "value"]]
                    m_time += time.time() - m_start

                    # load forecasted points
                    f_start = time.time()
                    # df_f = pd.DataFrame(element.forecasteddatapoints.all().values())
                    # df_f = pd.DataFrame(forecasteddatapoints.filter(element_id=pk))
                    df_f = df_f_all[df_f_all["element_id"] == int(pk)]
                    if not df_f.empty:
                        df_f = df_f.groupby("date").mean().reset_index()[["date", "value"]]
                    f_time += time.time() - f_start

                    df = pd.concat([df_m, df_f], ignore_index=True)
                    df["t"] = df["date"].apply(datetime.toordinal)
                    model.points[pk] = df[["t", "value"]].values.tolist()
                    model.converter(pk).equation = sd.lookup(sd.time(), pk)
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
                    df["date"] = df.apply(lambda row: date(row["year"], row["month"], row["day"]), axis=1)

                df["t"] = df["date"].apply(datetime.toordinal)
                model.points[pk] = df[["t", "value"]].values.tolist()
                model.converter(pk).equation = sd.lookup(sd.time(), pk)
            else:
                if pk in model_output_pks: model_output_pks.remove(pk)

    print(f"m took {m_time}, f took {f_time}")

    stop = time.time()
    print(f"set up inputs took {stop - start} s")
    start = time.time()

    # smoothed variables
    for element in smoothed_elements:
        pk = str(element.pk)
        # exec is limited to use sd.* and smooth functions, and can only see and edit the dict model_locals
        exec(f"temp_eq = {element.equation}", {"__builtins__": None, "sd": sd, "smooth": smooth}, model_locals)
        model.converter(pk).equation = model_locals.get("temp_eq")

    stop = time.time()
    print(f"set up smoothed variables took {stop - start} s")
    start = time.time()

    # set constant values
    constants_values = {}
    for element in elements:
        if element.sd_type == "Constant":
            try:
                constants_values[str(element.pk)] = element.constantvalues.get(
                    responseoption_id=responseoption_pk).value
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
    model_env.register_scenarios(scenarios={bptk_scenario: {"constants": constants_values}},
                                 scenario_manager="scenario_manager")
    # ignore pandas PerformanceWarnings since bptk will always throw these up if given enough variables to output
    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=pd.errors.PerformanceWarning)
        df = model_env.plot_scenarios(scenarios=bptk_scenario, scenario_managers="scenario_manager",
                                      equations=model_output_pks, return_df=True).reset_index()
    stop = time.time()
    print(f"run model took {stop - start} s")
    start = time.time()

    df["date"] = df["t"].apply(datetime.fromordinal)
    df = pd.melt(df, id_vars=["date"], value_vars=model_output_pks)

    stop = time.time()
    print(f"format results took {stop - start} s")
    start = time.time()

    # delete and save done with raw SQL delete and insert (twice as fast as built-in bulk_create)
    data = []
    for row in df.itertuples():
        data.extend([row.variable, row.value, row.date, scenario_pk, responseoption_pk])

    print(f"SQL iterrows took {time.time() - start} s")
    start = time.time()

    insert_stmt = (
        "INSERT INTO sahel_simulateddatapoint (element_id, value, date, scenario_id, responseoption_id) "
        f"VALUES {', '.join(['(%s, %s, %s, %s, %s)'] * len(df))}"
    )
    delete_stmt = (
        f"DELETE FROM sahel_simulateddatapoint WHERE "
        f"scenario_id = {scenario_pk} AND responseoption_id = {responseoption_pk}"
    )
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


def read_results(element_pk, scenario_pks, response_pks, agg_value: str = None):
    # initialize
    baseline_response_pk = 1
    response_pks_filter = response_pks.copy()
    if baseline_response_pk not in response_pks:
        response_pks_filter.append(baseline_response_pk)

    element = Variable.objects.get(pk=element_pk)
    if agg_value is None:
        agg_value = element.aggregate_by

    # read in element df
    df = pd.DataFrame(SimulatedDataPoint.objects.filter(
        element_id=element_pk,
        scenario_id__in=scenario_pks,
        responseoption_id__in=response_pks_filter,
    ).values("responseoption_id", "scenario_id", "value",
             "responseoption__name", "scenario__name", "date"))
    if "FCFA" in element.unit:
        df["value"] /= 1000
        element.unit = "1000 " + element.unit
    # must be sorted by date last
    df = df.sort_values(["scenario_id", "responseoption_id", "date"])

    # group by response and scenario
    df_agg = df.groupby([
        "responseoption_id", "scenario_id", "responseoption__name", "scenario__name"
    ])["value"]
    period = (df["date"].iloc[1] - df["date"].iloc[0]).days

    # perform correct aggregation
    if agg_value == "MEAN":
        df_agg = df_agg.mean().reset_index()
        agg_unit = element.unit
        agg_text = "moyen"
    elif agg_value == "SUM":
        agg_text = "total"
        df_agg = df_agg.sum().reset_index()
        df_agg["value"] *= period
        if "mois" in element.unit:
            df_agg["value"] /= 30.437
            agg_unit = element.unit.removesuffix(" / mois")
        elif "jour" in element.unit:
            agg_unit = element.unit.removesuffix(" / jour")
        elif "an" in element.unit:
            df_agg["value"] /= 365.25
            agg_unit = element.unit.removesuffix(" / an")
        else:
            agg_unit = "INCORRECT UNIT"
    elif "CHANGE" in agg_value:
        agg_text = "change"
        df_agg_initial = df_agg.nth(0)
        df_agg_final = df_agg.nth(-1)
        df_agg = df_agg_final - df_agg_initial
        agg_unit = element.unit
        if "%" in agg_value:
            df_agg *= 100 / df_agg_initial
            agg_unit = "%"
            agg_text = "% change"
        df_agg = df_agg.reset_index()
    else:
        print("invalid aggregation")
        agg_text = "INVALID"
        agg_unit = "INVALID"

    # read in cost df
    df_cost = pd.DataFrame(SimulatedDataPoint.objects.filter(
        element_id=102,
        scenario_id__in=scenario_pks,
        responseoption_id__in=response_pks_filter,
    ).values("responseoption_id", "scenario_id", "value",
             "responseoption__name", "scenario__name", "date"))
    df_cost = df_cost.sort_values(["scenario_id", "responseoption_id", "date"])
    df_cost_agg = df_cost.groupby([
        "responseoption_id", "scenario_id",
        "responseoption__name", "scenario__name"
    ]).sum().reset_index()
    df_cost_agg["value"] *= period / 30.437

    # calculate cost efficiency
    for scenario_pk in scenario_pks:
        baseline_value = df_agg.loc[(df_agg["scenario_id"] == scenario_pk) &
                                (df_agg["responseoption_id"] == baseline_response_pk)]["value"]
        baseline_cost = df_cost_agg.loc[(df_cost_agg["scenario_id"] == scenario_pk) &
                                    (df_cost_agg["responseoption_id"] == baseline_response_pk)]["value"]
        df_agg.loc[df_agg["scenario_id"] == scenario_pk, "baseline_value"] = float(baseline_value)
        df_cost_agg.loc[df_cost_agg["scenario_id"] == scenario_pk, "baseline_cost"] = float(baseline_cost)

    divider = 1000000 if element.unit in ["1", "tête"] else 1000
    divider_text = f"{divider:,}".replace(",", " ")
    df_agg["cost_eff"] = (
            (df_agg["value"] - df_agg["baseline_value"]) /
            (df_cost_agg["value"] - df_cost_agg["baseline_cost"]) * divider
    )
    df_agg["baseline_diff"] = df_agg["value"] - df_agg["baseline_value"]

    return df, df_cost, df_agg, df_cost_agg, agg_text, agg_unit, divider_text

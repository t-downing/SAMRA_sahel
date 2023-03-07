import pandas as pd
from BPTK_Py import Model, bptk
from BPTK_Py import sd_functions as sd
from ..models import Variable, SimulatedDataPoint, MeasuredDataPoint, ResponseConstantValue, ResponseOption, \
    SeasonalInputDataPoint, ForecastedDataPoint, HouseholdConstantValue, ScenarioConstantValue, PulseValue
from datetime import datetime, date
import time, functools, warnings
from django.db.models import Q
from django.db import connection
from contextlib import closing
from samra.settings import DATABASES

DAYS_IN_MONTH = 30.437


def run_model(
        scenario_pks: list[int],
        response_pks: list[int],
        samramodel_pk: int,
        adm0: str,
        adm1: str = None,
        adm2: str = None,
        startdate: date = date(2022, 7, 1),
        enddate: date = date(2024, 7, 1),
        timestep: int = 2,
):
    start = time.time()

    scenario_pks = [int(pk) for pk in scenario_pks]
    response_pks = [int(pk) for pk in response_pks]
    samramodel_pk = int(samramodel_pk)

    model = Model(starttime=startdate.toordinal(), stoptime=enddate.toordinal(), dt=timestep)
    zero_flow = model.flow("Zero Flow")
    zero_flow.equation = 0.0

    elements = Variable.objects.filter(samramodel_id=samramodel_pk).filter(
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
            # TODO: remove below line somehow
            model.constant(pk).equation = element.constant_default_value
        elif element.sd_type == "Pulse Input":
            model_locals.update({f'_E{element.pk}_': model.converter(pk)})
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
            initial_value_var_pk = element.stock_initial_value_variable_id
            if initial_value_var_pk is not None:
                model.stock(pk).initial_value = model.constant(str(element.stock_initial_value_variable_id))
            else:
                print(f"couldn't find initial_value_variable for {element}, setting initial value to 1.0")
                model.stock(pk).initial_value = 1.0
            for inflow in element.inflows.filter(equation__isnull=False).exclude(equation=""):
                model.stock(pk).equation += model.flow(inflow.pk) / DAYS_IN_MONTH if "mois" in inflow.unit else 1.0
            for outflow in element.outflows.filter(equation__isnull=False).exclude(equation=""):
                if "mois" in outflow.unit:
                    model.stock(pk).equation -= model.flow(outflow.pk) / DAYS_IN_MONTH
                else:
                    model.stock(pk).equation -= model.flow(outflow.pk)

    stop = time.time()
    print(f"set up equations took {stop - start} s")
    start = time.time()

    # read inputs
    mdps = MeasuredDataPoint.objects.filter(date__gte=startdate, date__lte=enddate, admin0=adm0)
    fdps = ForecastedDataPoint.objects.filter(date__gte=startdate, date__lte=enddate, admin0=adm0)
    sdps = SeasonalInputDataPoint.objects.filter(admin0=adm0)
    if adm1 is not None:
        mdps = mdps.filter(admin1=adm1)
        fdps = fdps.filter(admin1=adm1)
        sdps = sdps.filter(admin1=adm1)
        if adm2 is not None:
            mdps = mdps.filter(admin2=adm2)
            fdps = fdps.filter(admin2=adm2)
            sdps = sdps.filter(admin2=adm2)
    df_m_all = pd.DataFrame(mdps.values())
    df_f_all = pd.DataFrame(fdps.values())
    df_s_all = pd.DataFrame(sdps.values())

    m_time = 0.0
    f_time = 0.0

    # set inputs
    for element in elements:
        pk = str(element.pk)
        if element.sd_type in ["Input", "Seasonal Input"]:
            if f"_E{element.pk}_" in all_equations:
                if element.sd_type == "Input":
                    # load measured points
                    m_start = time.time()
                    df_m = df_m_all[df_m_all["element_id"] == int(pk)]
                    if not df_m.empty:
                        df_m = df_m.groupby("date").mean().reset_index()[["date", "value"]]
                    m_time += time.time() - m_start

                    # load forecasted points
                    f_start = time.time()
                    df_f = pd.DataFrame()
                    if not df_f_all.empty:
                        df_f = df_f_all[df_f_all["element_id"] == int(pk)]
                        if not df_f.empty:
                            df_f = df_f.groupby("date").mean().reset_index()[["date", "value"]]
                    f_time += time.time() - f_start
                    df = pd.concat([df_m, df_f], ignore_index=True)
                    if df.empty:
                        default_value = element.constant_default_value
                        print(f'{default_value=}')
                        if default_value is None: default_value = 0.0
                        print(f"couldn't find timeseries data for {element}, setting eq to {default_value}")
                        model.converter(pk).equation = default_value
                        continue
                else:
                    df = pd.DataFrame()
                    if not df_s_all.empty:
                        df = df_s_all[df_s_all['element_id'] == int(pk)]
                    if df.empty:
                        model.converter(str(element.pk)).equation = 1.0
                        print(f"couldn't find seasonal values for {element}, setting eq to 1.0")
                        continue
                    df["date"] = pd.to_datetime(df["date"])
                    df["month"] = df["date"].dt.month
                    df["day"] = df["date"].dt.day
                    df = df[['month', 'day', 'value']]
                    for yearnum in range(startdate.year - 1, enddate.year + 2):
                        df[f"year_{yearnum}"] = yearnum
                    df = pd.melt(df, id_vars=["value", "month", "day"], value_name="year")
                    df["date"] = df.apply(lambda row: date(row["year"], row["month"], row["day"]), axis=1)

                df["t"] = df["date"].apply(datetime.toordinal)
                model.points[pk] = df[["t", "value"]].values.tolist()
                model.converter(pk).equation = sd.lookup(sd.time(), pk)
            else:
                # print(f"{element} not used in any equations, removing from modeling")
                if pk in model_output_pks:
                    model_output_pks.remove(pk)

    print(f"m took {m_time}, f took {f_time}")

    stop = time.time()
    print(f"set up inputs took {stop - start} s")
    start = time.time()

    # smoothed variables
    # TODO: check if there's a problem setting smoothed variables before constants
    for element in smoothed_elements:
        pk = str(element.pk)
        print(element.label)
        # exec is limited to use sd.* and smooth functions, and can only see and edit the dict model_locals
        exec(f"temp_eq = {element.equation}", {"__builtins__": None, "sd": sd, "smooth": smooth}, model_locals)
        model.converter(pk).equation = model_locals.get("temp_eq")

    stop = time.time()
    print(f"set up smoothed variables took {stop - start} s")
    start = time.time()

    # set constant values
    constants_values = {}
    response_cv_df = pd.DataFrame(ResponseConstantValue.objects.filter(admin0=adm0).values())
    response_pv_df = pd.DataFrame(PulseValue.objects.filter(admin0=adm0).values())
    scenario_cv_df = pd.DataFrame(ScenarioConstantValue.objects.filter().values())
    household_cv_df = pd.DataFrame(HouseholdConstantValue.objects.filter(admin0=adm0).values())
    print(f"{response_pv_df=}")

    household_constants = {}
    if not household_cv_df.empty:
        household_constants.update({
            str(row.element_id): row.value
            for row in household_cv_df.itertuples()
        })

    for scenario_pk in scenario_pks:
        print(f"SETTING UP SCENARIO {scenario_pk}")
        scenario_constants = {}
        if not scenario_cv_df.empty:
            scenario_cv_dff = scenario_cv_df[scenario_cv_df['scenario_id'] == scenario_pk]
            if not scenario_cv_dff.empty:
                scenario_constants.update({
                    str(row.element_id): row.value
                    for row in scenario_cv_dff.itertuples()
                })
        for responseoption_pk in response_pks:
            print(f"SETTING UP RESPONSE {responseoption_pk}")
            response_constants = {}
            if not response_cv_df.empty:
                response_cv_dff = response_cv_df[response_cv_df['responseoption_id'] == responseoption_pk]
                if not response_cv_dff.empty:
                    response_constants.update({
                        str(row.element_id): row.value
                        for row in response_cv_dff.itertuples()
                    })

            response_pv_dff = pd.DataFrame()
            if not response_pv_df.empty:
                response_pv_dff = response_pv_df[response_pv_df['responseoption_id'] == responseoption_pk]
            print(f"{response_pv_dff=}")
            # check that constants are all there and set pulses
            constants = household_constants | scenario_constants | response_constants
            for element in elements:
                pk = str(element.pk)
                if element.sd_type in Variable.CONSTANTS:
                    if pk not in constants:
                        print(f"couldn't find constant for {element}, setting to 0.0")
                        household_constants.update({pk: 0.0})
                elif element.sd_type == Variable.RESPONSE_PULSE:
                    model.converter(pk).equation = 0.0
                    if not response_pv_dff.empty:
                        response_pv_dfff = response_pv_dff[response_pv_dff['element_id'] == int(pk)]
                        print(f"{response_pv_dfff=}")
                        for row in response_pv_dfff.itertuples():
                            pulse_start_ord = (row.startdate - pd.DateOffset(days=15)).toordinal()
                            pulse_stop_ord = (row.startdate + pd.DateOffset(days=15)).toordinal()
                            model.converter(pk).equation += sd.If(
                                sd.And(sd.time() > pulse_start_ord, sd.time() < pulse_stop_ord), row.value, 0.0
                            )
                    else:
                        print(f"couldn't find pulses for {element}, setting to 0.0")

            stop = time.time()
            print(f"setup constants took {stop - start} s")
            start = time.time()

            # setup to run model
            model_env = bptk()
            model_env.register_model(model)
            scenario_manager = {"scenario_manager": {"model": model}}
            model_env.register_scenario_manager(scenario_manager)

            # run model
            # for purposes of running bptk, just set scenario to "base"
            # TODO: loop over admin0s and/or HH types
            bptk_scenario = "base"
            model_env.register_scenarios(scenarios={bptk_scenario: {"constants": constants}},
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
            df = df.drop(columns=['t'])
            df = pd.melt(df, id_vars=["date"])

            pks_in_result = df['variable'].unique()
            missing_pks = []
            for pk in model_output_pks:
                if pk not in pks_in_result:
                    missing_pks.append(pk)

            missing_variables = Variable.objects.filter(pk__in=missing_pks)
            print(missing_variables)

            stop = time.time()
            print(f"format results took {stop - start} s")
            start = time.time()

            if DATABASES['default']['ENGINE'] == 'mssql':
                # if using MSSQL, use Django ORM because there's a problem with using the raw SQL
                # TODO: add admin0-2 functionality
                objs = [
                    SimulatedDataPoint(
                        element_id=row.variable,
                        value=row.value,
                        date=row.date,
                        scenario_id=scenario_pk,
                        responseoption_id=responseoption_pk
                    )
                    for row in df.itertuples()
                ]

                print(f"df iterrows took {time.time() - start} s")
                start = time.time()

                SimulatedDataPoint.objects.filter(scenario_id=scenario_pk, responseoption_id=responseoption_pk).delete()
                SimulatedDataPoint.objects.bulk_create(objs)

                print(f"bulk_create took {time.time() - start} s")
                start = time.time()
            else:
                # delete and save done with raw SQL delete and insert (twice as fast as built-in bulk_create)
                # TODO: add admin1-2 functionality
                data = []
                for row in df.itertuples():
                    data.extend([row.variable, row.value, row.date, scenario_pk, responseoption_pk, adm0])

                print(f"SQL iterrows took {time.time() - start} s")
                start = time.time()

                insert_stmt = (
                    "INSERT INTO sahel_simulateddatapoint (element_id, value, date, scenario_id, responseoption_id, admin0) "
                    f"VALUES {', '.join(['(' + ', '.join(['%s'] * 6) + ')'] * len(df))}"
                )
                delete_stmt = (
                    f"DELETE FROM sahel_simulateddatapoint WHERE "
                    f"scenario_id = {scenario_pk} AND responseoption_id = {responseoption_pk} AND admin0 = '{adm0}';"
                )
                with closing(connection.cursor()) as cursor:
                    cursor.execute(delete_stmt)
                    cursor.execute(insert_stmt, data)

                print(f"SQL bulk delete and insert took {time.time() - start} s")
                start = time.time()

    return None


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


def read_results(adm0, element_pk, scenario_pks, response_pks, agg_value: str = None):
    # TODO: again, add admin1-2
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
        admin0=adm0,
        element_id=element_pk,
        scenario_id__in=scenario_pks,
        responseoption_id__in=response_pks_filter,
    ).values("responseoption_id", "scenario_id", "value",
             "responseoption__name", "scenario__name", "date"))
    if "LCY" in element.unit:
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
        admin0=adm0,
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
    df_cost_agg["value"] *= period / DAYS_IN_MONTH

    # calculate cost efficiency
    for scenario_pk in scenario_pks:
        baseline_value = df_agg.loc[(df_agg["scenario_id"] == scenario_pk) &
                                (df_agg["responseoption_id"] == baseline_response_pk)]["value"]
        baseline_cost = df_cost_agg.loc[(df_cost_agg["scenario_id"] == scenario_pk) &
                                    (df_cost_agg["responseoption_id"] == baseline_response_pk)]["value"]
        print(f'{baseline_value=}')
        print(f'{baseline_cost=}')
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

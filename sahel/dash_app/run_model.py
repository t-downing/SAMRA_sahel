import numpy as np
import pandas as pd
from BPTK_Py import Model, bptk
from BPTK_Py import sd_functions as sd
from ..models import Element, SimulatedDataPoint, MeasuredDataPoint, ConstantValue, ResponseOption, SeasonalInputDataPoint
from datetime import datetime, date
import time
from django.conf import settings
from sqlalchemy import create_engine
from django.db.models import Q


def run_model(scenario: str = "default_scenario", responseoption_pk: int = 1):
    start = time.time()
    startdate, enddate = date(2021, 1, 1), date(2022, 1, 1)

    model = Model(starttime=startdate.toordinal(), stoptime=enddate.toordinal(), dt=1)
    zero_flow = model.flow("Zero Flow")
    zero_flow.equation = 0.0

    elements = Element.objects.filter(
        Q(sd_type="Variable", equation__isnull=False) |
        Q(sd_type="Flow", equation__isnull=False) |
        Q(sd_type="Stock") |
        Q(sd_type="Input") |
        Q(sd_type="Seasonal Input") |
        Q(sd_type="Constant")
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
        elif element.sd_type == "Constant":
            exec(f'_E{element.pk}_ = model.constant("{element.pk}")')
            model.constant(str(element.pk)).equation = element.constant_default_value
    stop = time.time()
    print(f"set up elements took {stop - start} s")
    start = time.time()

    # set equations for modeling elements
    all_equations = ""
    for element in elements:
        # used it once, might as well use it again
        if element.sd_type in ["Variable", "Flow"]:
            try:
                exec(f'_E{element.pk}_.equation = {element.equation}')
                # if element.unit is not None:
                #     if "mois" in element.unit:
                #         if element.sd_type == "Variable":
                #             model.converter(str(element.pk)).equation /= 30.437
                #         else:
                #             model.flow(str(element.pk)).equation /= 30.437
                all_equations += element.equation
            except NameError as error:
                print(f"'{element}' equation could not be defined because {error}. "
                      f"Setting equation to 0.0 instead.")
                exec(f'_E{element.pk}_.equation = 0.0')

        elif element.sd_type == "Stock":
            model.stock(str(element.pk)).equation = zero_flow
            exec(f'model.stock(str({element.pk})).initial_value = {element.equation}')
            for inflow in element.inflows.filter(equation__isnull=False).exclude(equation=""):
                if "mois" in inflow.unit:
                    model.stock(str(element.pk)).equation += model.flow(inflow.pk) / 30.437
                else:
                    model.stock(str(element.pk)).equation += model.flow(inflow.pk)
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
                    df = pd.DataFrame(MeasuredDataPoint.objects.filter(element=element).values())
                    df = df.groupby("date").mean().reset_index()[["date", "value"]]
                    df["t"] = df["date"].apply(datetime.toordinal)
                    model.points[str(element.pk)] = df[["t", "value"]].values.tolist()
                    model.converter(str(element.pk)).equation = sd.lookup(sd.time(), str(element.pk))
                else:
                    df = pd.DataFrame(SeasonalInputDataPoint.objects.filter(element=element).values())
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

    # set constant values
    constants_values = {}
    if responseoption_pk is not None:
        responseoption = ResponseOption.objects.get(pk=responseoption_pk)
        for element in elements:
            if element.sd_type == "Constant":
                try:
                    constants_values[str(element.pk)] = element.constantvalues.get(responseoption=responseoption).value
                    print(f"set {element} constant to {responseoption} value")
                except ConstantValue.DoesNotExist:
                    pass


    model_env = bptk()
    model_env.register_model(model)
    scenario_manager = {"scenario_manager": {"model": model}}
    model_env.register_scenario_manager(scenario_manager)

    model_env.register_scenarios(scenarios={scenario: {"constants": constants_values}}, scenario_manager="scenario_manager")
    df = model_env.plot_scenarios(scenarios=scenario, scenario_managers="scenario_manager", equations=model_output_pks, return_df=True).reset_index()

    stop = time.time()
    print(f"run model took {stop - start} s")
    start = time.time()

    df["date"] = df["t"].apply(datetime.fromordinal)
    # for element in elements:
    #     if str(element.pk) in df.columns:
    #         if "mois" in element.unit:
    #             df[str(element.pk)] *= 30.437
    df = pd.melt(df, id_vars=["date"], value_vars=model_output_pks)
    df = df.groupby(["variable", pd.Grouper(key="date", freq="W-MON")]).mean().reset_index()

    stop = time.time()
    print(f"format results took {stop - start} s")
    start = time.time()

    simulationdatapoint_list = [
        SimulatedDataPoint(
            element_id=row.variable,
            value=row.value,
            date=row.date,
            scenario=scenario,
            responseoption=responseoption
        )
        for row in df.itertuples()
    ]

    stop = time.time()
    print(f"df iterrows took {stop - start} s")
    start = time.time()

    SimulatedDataPoint.objects.filter(scenario=scenario, responseoption=responseoption).delete()
    SimulatedDataPoint.objects.bulk_create(simulationdatapoint_list)

    stop = time.time()
    print(f"delete and save took {stop - start} s")

    # database_name = settings.DATABASES['default']['NAME']
    # database_url = 'sqlite:///{database_name}'.format(database_name=database_name)
    # engine = create_engine(database_url, echo=False)
    # print(df)
    # df.to_sql("simulateddatapoint", con=engine, if_exists='append')

    return df
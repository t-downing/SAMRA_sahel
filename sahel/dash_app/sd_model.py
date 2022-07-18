import pandas as pd
from BPTK_Py import Model, bptk
from ..models import Element, SimulatedDataPoint
from datetime import datetime


def run_model(scenario: str = "default_scenario"):
    startdate, enddate = datetime(2022, 1, 1), datetime(2022, 2, 1)

    model = Model(starttime=startdate.toordinal(), stoptime=enddate.toordinal(), dt=1)
    zero_flow = model.flow("Zero Flow")
    zero_flow.equation = 0.0

    elements = Element.objects.filter(equation__isnull=False)

    element_pks = [str(element.pk) for element in elements]

    for element in elements:
        # so so sorry for using exec, this is the way life must be for now
        if element.sd_type == "Variable":
            exec(f'_E{element.pk}_ = model.converter("{element.pk}")')
        elif element.sd_type == "Flow":
            exec(f'_E{element.pk}_ = model.flow("{element.pk}")')
        elif element.sd_type == "Stock":
            exec(f'_E{element.pk}_ = model.stock("{element.pk}")')

    for element in elements:
        # used it once, might as well use it again
        if element.sd_type in ["Variable", "Flow"]:
            exec(f'_E{element.pk}_.equation = {element.equation}')
        elif element.sd_type == "Stock":
            model.stock(str(element.pk)).equation = zero_flow
            model.stock(str(element.pk)).initial_value = 0.0
            for inflow in element.inflows.filter(equation__isnull=False):
                model.stock(str(element.pk)).equation += model.flow(inflow.pk)
            for outflow in element.outflows.filter(equation__isnull=False):
                model.stock(str(element.pk)).equation -= model.flow(outflow.pk)

    model_env = bptk()
    model_env.register_model(model)
    scenario_manager = {"scenario_manager": {"model": model}}
    model_env.register_scenario_manager(scenario_manager)

    model_env.register_scenarios(scenarios={scenario: {"constants": {}}}, scenario_manager="scenario_manager")
    df = model_env.plot_scenarios(scenarios=scenario, scenario_managers="scenario_manager", equations=element_pks, return_df=True).reset_index()
    df["scenario"] = scenario
    df["date"] = df["t"].apply(datetime.fromordinal)
    df = pd.melt(df, id_vars=["date", "scenario"], value_vars=element_pks)

    simulationdatapoint_list = []

    for index, row in df.iterrows():
        simulationdatapoint_list.append(SimulatedDataPoint(
            element=Element.objects.get(pk=row["variable"]),
            value=row["value"],
            date=row["date"],
            scenario=row["scenario"]
        ))

    SimulatedDataPoint.objects.filter(scenario=scenario).delete()
    SimulatedDataPoint.objects.bulk_create(simulationdatapoint_list)

    return df
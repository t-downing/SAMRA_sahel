from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Element, Scenario

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
import pandas as pd

app = DjangoDash("scenarioresponse", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(fluid=True, style={"background-color": "#f8f9fc"}, children=[
    dbc.Row([
        dbc.Col(width=2, children=[
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardHeader("Filtres", id="filters"),
                dbc.CardBody([
                    dbc.Select(id="element-input", className="mb-2", size="sm"),
                    html.H5("Scénarios:"),
                    dbc.Checklist(id="scenario-input", className="mb-2"),
                    html.H5("Réponses:"),
                    dbc.Checklist(id="response-input", className="mb-2"),
                ])
            ])
        ]),
        dbc.Col(width=10, children=[
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardBody(dcc.Graph(id="bar-graph"))
            ])
        ])
    ]),
    dbc.Row([
        dbc.Col(width=6, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(dcc.Graph(id="time-graph"))
            ])
        ]),
        dbc.Col(width=6, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(dcc.Graph(id="scatter-graph"))
            ])
        ])
    ]),
    dbc.Row([
        dbc.Col(width=12, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(dcc.Graph(id="eff-graph"))
            ])
        ])
    ])
])


@app.callback(
    Output("element-input", "options"),
    Output("element-input", "value"),
    Output("scenario-input", "options"),
    Output("scenario-input", "value"),
    Output("response-input", "options"),
    Output("response-input", "value"),
    Input("filters", "children")
)
def populate_initial(_):
    element_options = [{"label": element.label, "value": element.pk}
                       for element in Element.objects.exclude(simulateddatapoints=None)]
    element_value = 77
    scenario_options = [{"label": scenario.name, "value": scenario.pk}
                        for scenario in Scenario.objects.all()]
    scenario_value = [scenario.get("value") for scenario in scenario_options]
    response_options = [{"label": scenario.name, "value": scenario.pk}
                        for scenario in ResponseOption.objects.all()]
    response_value = [response.get("value") for response in response_options]
    return element_options, element_value, scenario_options, scenario_value, response_options, response_value


@app.callback(
    Output("bar-graph", "figure"),
    Output("time-graph", "figure"),
    Output("scatter-graph", "figure"),
    Output("eff-graph", "figure"),
    Input("element-input", "value"),
    Input("scenario-input", "value"),
    Input("response-input", "value")
)
def update_graphs(element_pk, scenario_pks, response_pks):
    response2color = {response_pk: color for response_pk, color in zip(response_pks, DEFAULT_PLOTLY_COLORS)}
    DASHES = ["solid", "dot", "dash", "longdash", "dashdot", "longdashdot"]
    scenario2dash = {scenario_pk: dash for scenario_pk, dash in zip(scenario_pks, DASHES)}
    element = Element.objects.get(pk=element_pk)
    df = pd.DataFrame(SimulatedDataPoint.objects.filter(
        element_id=element_pk,
        scenario_id__in=scenario_pks,
        responseoption_id__in=response_pks,
    ).values("responseoption_id", "scenario_id", "value",
             "responseoption__name", "scenario__name", "date"))

    df_agg = df.groupby([
        "responseoption_id", "scenario_id", "responseoption__name", "scenario__name"
    ])
    period = (df["date"].iloc[1] - df["date"].iloc[0]).days

    if element.aggregate_by == "MEAN":
        df_agg = df_agg.mean().reset_index()
        agg_unit = element.unit
        agg_text = "moyen"
    else:
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

    # bar graph
    bar_fig = go.Figure(layout=dict(template="simple_white"))
    for response_pk in response_pks:
        dff_agg = df_agg[df_agg["responseoption_id"] == response_pk]
        if dff_agg.empty:
            continue
        bar_fig.add_trace(go.Bar(
            name=dff_agg.iloc[0].responseoption__name,
            x=dff_agg["scenario__name"],
            y=dff_agg["value"],
            text=dff_agg["value"].apply(lambda value: f"{value:.2}<br>{agg_unit}"),
            marker_color=response2color.get(response_pk)
        ))
    bar_fig.update_layout(barmode="group", showlegend=True, legend=dict(title="Réponse"),
                          title_text=f"{element.label}: {agg_text}")
    bar_fig.update_yaxes(visible=False)
    bar_fig.update_xaxes(ticklen=0, showline=False)
    bar_fig.add_hline(y=0, line_width=1, line_color="black", opacity=1)

    # time graph
    time_fig = go.Figure(layout=dict(template="simple_white"))
    for scenario_pk in scenario_pks:
        for response_pk in response_pks:
            dff = df[(df["responseoption_id"] == response_pk) &
                     (df["scenario_id"] == scenario_pk)]
            if dff.empty:
                continue
            time_fig.add_trace(go.Scatter(
                x=dff["date"],
                y=dff["value"],
                name=dff["responseoption__name"].iloc[0],
                legendgroup=dff["scenario__name"].iloc[0],
                legendgrouptitle_text=dff["scenario__name"].iloc[0],
                line=dict(color=response2color.get(response_pk), dash=scenario2dash.get(scenario_pk)),
            ))

    time_fig.update_layout(showlegend=True, title_text=f"{element.label}: chronologie")
    time_fig.update_xaxes(title_text="Date")
    time_fig.update_yaxes(title_text=f"{element.label} ({element.unit})")


    # scatter graph
    df_cost = pd.DataFrame(SimulatedDataPoint.objects.filter(
        element_id=102,
        scenario_id__in=scenario_pks,
        responseoption_id__in=response_pks,
    ).values("responseoption_id", "scenario_id", "value",
             "responseoption__name", "scenario__name", "date"))
    df_cost_agg = df_cost.groupby([
        "responseoption_id", "scenario_id",
        "responseoption__name", "scenario__name"
    ]).sum().reset_index()
    df_cost_agg["value"] *= period / 30.437

    scatter_fig = go.Figure(layout=dict(template="simple_white"))
    show_response_legend = True
    for scenario_pk in scenario_pks:
        dff_cost_agg = df_cost_agg[df_cost_agg["scenario_id"] == scenario_pk]
        dff_agg = df_agg[df_cost_agg["scenario_id"] == scenario_pk]
        if dff_agg.empty:
            continue
        scatter_fig.add_trace(go.Scatter(
            x=dff_cost_agg["value"],
            y=dff_agg["value"],
            mode="lines",
            line=dict(color="gray", width=1, dash=scenario2dash.get(scenario_pk)),
            legendgroup="Scénario",
            legendgrouptitle_text="Scénario",
            name=dff_agg.iloc[0]["scenario__name"],
        ))
        for response_pk in response_pks:
            dfff_cost_agg = dff_cost_agg[dff_cost_agg["responseoption_id"] == response_pk]
            dfff_agg = dff_agg[dff_cost_agg["responseoption_id"] == response_pk]
            if dfff_agg.empty:
                continue
            scatter_fig.add_trace(go.Scatter(
                x=dfff_cost_agg["value"],
                y=dfff_agg["value"],
                mode="markers",
                marker_color=response2color.get(response_pk),
                name=dfff_agg.iloc[0]["responseoption__name"],
                showlegend=show_response_legend,
                legendgroup="Réponse",
                legendgrouptitle_text="Réponse",
            ))
        show_response_legend = False

    scatter_fig.update_layout(
        showlegend=True, title_text="Comparaison avec coûts",
    )
    scatter_fig.update_xaxes(title_text="Coûts totaux CICR (FCFA)")
    scatter_fig.update_yaxes(title_text=f"{element.label} {agg_text} ({agg_unit})")

    # effciency graph
    eff_fig = go.Figure(layout=dict(template="simple_white"))
    baseline_response_pk = 1
    for scenario_pk in scenario_pks:
        baseline_value = df_agg.loc[(df_agg["scenario_id"] == scenario_pk) &
                                (df_agg["responseoption_id"] == baseline_response_pk)]["value"]
        baseline_cost = df_cost_agg.loc[(df_cost_agg["scenario_id"] == scenario_pk) &
                                    (df_cost_agg["responseoption_id"] == baseline_response_pk)]["value"]
        df_agg.loc[df_agg["scenario_id"] == scenario_pk, "baseline_value"] = float(baseline_value)
        df_cost_agg.loc[df_cost_agg["scenario_id"] == scenario_pk, "baseline_cost"] = float(baseline_cost)

    df_agg["cost_eff"] = (
            (df_agg["value"] - df_agg["baseline_value"]) /
            (df_cost_agg["value"] - df_cost_agg["baseline_cost"]) * 1000
    )

    for response_pk in response_pks:
        if response_pk == baseline_response_pk:
            continue
        dff_agg = df_agg[df_agg["responseoption_id"] == response_pk]
        if dff_agg.empty:
            continue
        eff_fig.add_trace(go.Bar(
            name=dff_agg.iloc[0].responseoption__name,
            x=dff_agg["scenario__name"],
            y=dff_agg["cost_eff"],
            text=dff_agg["cost_eff"].apply(lambda value: f"{value:.2}<br>{agg_unit} / 1000 FCFA"),
            marker_color=response2color.get(response_pk)
        ))

    eff_fig.update_layout(barmode="group", showlegend=True, legend=dict(title="Réponse"),
                          title_text=f"Rapport coût-efficacité contre {ResponseOption.objects.get(pk=baseline_response_pk)}",
                          )
    eff_fig.update_yaxes(visible=False)
    eff_fig.update_xaxes(ticklen=0, showline=False)
    eff_fig.add_hline(y=0, line_width=1, line_color="black", opacity=1)


    return bar_fig, time_fig, scatter_fig, eff_fig

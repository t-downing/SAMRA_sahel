import time
import datetime

from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Variable, Scenario, ADMIN0S, CURRENCY
from sahel.sd_model.model_operations import run_model, timer, read_results

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
import itertools
import pandas as pd

DASHES = ["solid", "dot", "dash", "longdash", "dashdot", "longdashdot"]
DEFAULT_ADM0 = 'Mauritanie'
DEFAULT_SAMRAMODEL_PK = 1
DEFAULT_RESPONSE_PKS = [1, 2, 3, 5, 14]

app = DjangoDash("scenarioresponse", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(fluid=True, style={"background-color": "#f8f9fc"}, children=[
    html.Div(id=(INIT := "init"), hidden=True, children='init'),
    dbc.Row([
        dbc.Col(width=2, children=[
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardBody([
                    dbc.Select(id=(ADMIN0_INPUT := "admin0-input"), className="mb-2", style={"font-size": "small"}),
                    dbc.Select(id=(VARIABLE_INPUT := "variable-input"), className="mb-2", style={"font-size": "small"}),
                    dbc.Select(id=(AGG_INPUT := "agg-input"), className="mb-2", style={"font-size": "small"}),
                    html.H6("Scénarios:"),
                    dbc.Checklist(id=(SCENARIO_INPUT := "scenario-input"), className="mb-2",
                                  style={"font-size": "small"}),
                    html.H6("Réponses:"),
                    dbc.Checklist(id=(RESPONSE_INPUT := "response-input"), className="mb-2",
                                  style={"height": "195px", "overflow-y": "scroll", "font-size": "small"}),
                    dbc.Button("Réexécuter", id="rerun-submit", color="danger", size="sm", disabled=False),
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
    ]),
    html.Div(id=(RERUN_READOUT := "rerun-readout")),
])


@app.callback(
    Output(VARIABLE_INPUT, "options"),
    Output(VARIABLE_INPUT, "value"),
    Output(AGG_INPUT, "options"),
    Output(ADMIN0_INPUT, "options"),
    Output(ADMIN0_INPUT, "value"),
    Output(SCENARIO_INPUT, "options"),
    Output(SCENARIO_INPUT, "value"),
    Output(RESPONSE_INPUT, "options"),
    Output(RESPONSE_INPUT, "value"),
    Input(INIT, "children")
)
@timer
def populate_initial(_):
    admin0_options = [{'label': adm0, 'value': adm0} for adm0 in ADMIN0S]
    admin0_value = DEFAULT_ADM0
    included_types = ["Stock", "Flow", "Variable"]
    variable_options = [
        {"label": element.get("label"), "value": element.get("id")}
        for element in Variable.objects.exclude(simulateddatapoints=None).filter(sd_type__in=included_types).values("id", "label")
    ]
    variable_value = 77
    agg_options = [{"label": agg[1], "value": agg[0]} for agg in Variable.AGG_OPTIONS]
    scenario_options = [
        {"label": scenario.get("name"), "value": scenario.get("id")}
        for scenario in Scenario.objects.all().order_by("id").values("id", "name")
    ]
    scenario_value = [scenario.get("value") for scenario in scenario_options]
    response_options = [
        {"label": obj.get("name"), "value": obj.get("id")}
        for obj in ResponseOption.objects.all().order_by("id").values("id", "name")
    ]
    response_value = DEFAULT_RESPONSE_PKS
    return (
        variable_options, variable_value, agg_options,
        admin0_options, admin0_value,
        scenario_options, scenario_value,
        response_options, response_value
    )


@app.callback(
    Output(AGG_INPUT, "value"),
    Input(VARIABLE_INPUT, "value"),
)
@timer
def update_default_agg(element_pk):
    return Variable.objects.get(pk=element_pk).aggregate_by


@app.callback(
    Output("rerun-readout", "children"),
    Input("rerun-submit", "n_clicks"),
    State(ADMIN0_INPUT, "value"),
    State(SCENARIO_INPUT, "value"),
    State(RESPONSE_INPUT, "value"),
)
@timer
def rerun_model(n_clicks, adm0, scenario_pks, response_pks):
    if n_clicks is None:
        raise PreventUpdate
    start = time.time()
    n = len(scenario_pks) * len(response_pks)
    startdate = datetime.date(2023, 1, 1)
    enddate = datetime.date(2025, 1, 1)
    run_model(scenario_pks, response_pks, DEFAULT_SAMRAMODEL_PK, adm0, startdate=startdate, enddate=enddate)
    stop = time.time()
    duration = stop - start
    duration_per = duration / n
    return f"ran scenarios{scenario_pks}; responses {response_pks}; {duration:.2f} total, {duration_per:.2f} per run"


@app.callback(
    Output("bar-graph", "figure"),
    Output("time-graph", "figure"),
    Output("scatter-graph", "figure"),
    Output("eff-graph", "figure"),
    Input(ADMIN0_INPUT, "value"),
    Input(VARIABLE_INPUT, "value"),
    Input(AGG_INPUT, "value"),
    Input(SCENARIO_INPUT, "value"),
    Input(RESPONSE_INPUT, "value"),
    Input(RERUN_READOUT, 'children'),
)
@timer
def update_graphs(adm0, element_pk, agg_value, scenario_pks, response_pks, _):
    # set colors
    baseline_response_pk = 1
    scenario_pks.sort()
    response_pks.sort()
    response2color = {response_pk: color
                      for response_pk, color in zip(response_pks[1:], itertools.cycle(DEFAULT_PLOTLY_COLORS))}
    response2color[baseline_response_pk] = "black"
    scenario2dash = {scenario_pk: dash for scenario_pk, dash in zip(scenario_pks, DASHES)}
    element = Variable.objects.get(pk=element_pk)

    # read results
    df, df_cost, df_agg, df_cost_agg, agg_text, agg_unit, divider_text, unit = read_results(
        adm0=adm0, element_pk=element_pk, scenario_pks=scenario_pks, response_pks=response_pks, agg_value=agg_value
    )
    agg_unit = agg_unit.replace('LCY', CURRENCY.get(adm0))

    # bar graph
    decimals = 2 if element.unit == "1" else 1
    bar_fig = go.Figure(layout=dict(template="simple_white"))
    for response_pk in response_pks:
        dff_agg = df_agg[df_agg["responseoption_id"] == response_pk]
        if dff_agg.empty:
            continue
        bar_fig.add_trace(go.Bar(
            name=dff_agg.iloc[0].responseoption__name,
            x=dff_agg["scenario__name"],
            y=dff_agg["value"],
            text=dff_agg["value"].round(decimals),
            marker_color=response2color.get(response_pk)
        ))
    bar_fig.update_layout(barmode="group", showlegend=True, legend=dict(title="Réponse"),
                          title_text=f"{element.label}: {agg_text}")
    bar_fig.update_yaxes(title_text=agg_unit)
    bar_fig.update_xaxes(ticklen=0, showline=False, tickfont_size=14)
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
    time_fig.update_yaxes(title_text=f"{element.label} ({unit})")

    # scatter graph
    scatter_fig = go.Figure(layout=dict(template="simple_white"))
    show_response_legend = True
    for scenario_pk in scenario_pks:
        dff_agg = df_agg.loc[df_cost_agg["scenario_id"] == scenario_pk]
        dff_agg.loc[:, "cost"] = df_cost_agg[df_cost_agg["scenario_id"] == scenario_pk]["value"]
        dff_agg = dff_agg.sort_values(["cost"])
        if dff_agg.empty:
            continue
        scatter_fig.add_trace(go.Scatter(
            x=dff_agg["cost"],
            y=dff_agg["value"],
            mode="lines",
            line=dict(color="gray", width=1, dash=scenario2dash.get(scenario_pk)),
            legendgroup="Scénario",
            legendgrouptitle_text="Scénario",
            name=dff_agg.iloc[0]["scenario__name"],
        ))
        for response_pk in response_pks:
            dfff_agg = dff_agg[dff_agg["responseoption_id"] == response_pk]
            if dfff_agg.empty:
                continue
            scatter_fig.add_trace(go.Scatter(
                x=dfff_agg["cost"],
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
    scatter_fig.update_xaxes(title_text=f"Coûts totaux CICR ({CURRENCY.get(adm0)})")
    scatter_fig.update_yaxes(title_text=f"{element.label} {agg_text} ({agg_unit})")

    # efficiency graph
    eff_fig = go.Figure(layout=dict(template="simple_white"))
    decimals = 1
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
            text=dff_agg["cost_eff"].round(decimals),
            marker_color=response2color.get(response_pk)
        ))

    eff_fig.update_layout(barmode="group", showlegend=True, legend=dict(title="Réponse"),
                          title_text=f"Rapport coût-efficacité contre {ResponseOption.objects.get(pk=baseline_response_pk)}"
                                     f" pour {element.label}",
                          )
    y_title = "1" if agg_unit == f"1000 {CURRENCY.get(adm0)}" else f"{agg_unit} / {divider_text} {CURRENCY.get(adm0)}"
    eff_fig.update_yaxes(title_text=y_title)
    eff_fig.update_xaxes(ticklen=0, showline=False, tickfont_size=14)
    eff_fig.add_hline(y=0, line_width=1, line_color="black", opacity=1)

    return bar_fig, time_fig, scatter_fig, eff_fig

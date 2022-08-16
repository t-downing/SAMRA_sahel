import time

from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Element, Scenario
from sahel.sd_model.model_operations import run_model

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
import itertools
import pandas as pd

app = DjangoDash("scenarioresponse", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(fluid=True, style={"background-color": "#f8f9fc"}, children=[
    dbc.Row([
        dbc.Col(width=2, children=[
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardBody([
                    html.Div(id="filters"),
                    dbc.Select(id="element-input", className="mb-2", style={"font-size": "small"}),
                    dbc.Select(id="agg-input", className="mb-2", style={"font-size": "small"}),
                    html.H6("Scénarios:"),
                    dbc.Checklist(id="scenario-input", className="mb-2", style={"font-size": "small"}),
                    html.H6("Réponses:"),
                    dbc.Checklist(id="response-input", className="mb-2",
                                  style={"height": "195px", "overflow-y": "scroll", "font-size": "small"}),
                    dbc.Button("Réexécuter", id="rerun-submit", color="danger", size="sm"),
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
    html.Div(id="rerun-readout")
])


@app.callback(
    Output("element-input", "options"),
    Output("element-input", "value"),
    Output("agg-input", "options"),
    Output("scenario-input", "options"),
    Output("scenario-input", "value"),
    Output("response-input", "options"),
    Output("response-input", "value"),
    Input("filters", "children")
)
def populate_initial(_):
    included_types=["Stock", "Flow", "Variable"]
    element_options = [{"label": element.label, "value": element.pk}
                       for element in Element.objects.exclude(simulateddatapoints=None).filter(sd_type__in=included_types)]
    element_value = 77
    agg_options = [{"label": agg[1], "value": agg[0]} for agg in Element.AGG_OPTIONS]
    scenario_options = [{"label": scenario.name, "value": scenario.pk}
                        for scenario in Scenario.objects.all()]
    scenario_value = [scenario.get("value") for scenario in scenario_options]
    response_options = [{"label": scenario.name, "value": scenario.pk}
                        for scenario in ResponseOption.objects.all()]
    response_value = [response.get("value") for response in response_options]
    return element_options, element_value, agg_options, scenario_options, scenario_value, response_options, response_value


@app.callback(
    Output("agg-input", "value"),
    Input("element-input", "value"),
)
def update_default_agg(element_pk):
    return Element.objects.get(pk=element_pk).aggregate_by


@app.callback(
    Output("rerun-readout", "children"),
    Input("rerun-submit", "n_clicks"),
    State("scenario-input", "value"),
    State("response-input", "value"),
)
def rerun_model(n_clicks, scenario_pks, response_pks):
    if n_clicks is None:
        raise PreventUpdate
    start = time.time()
    n = len(scenario_pks) * len(response_pks)
    for scenario_pk in scenario_pks:
        for response_pk in response_pks:
            run_model(scenario_pk=scenario_pk, responseoption_pk=response_pk)
    stop = time.time()
    duration = stop - start
    duration_per = duration / n
    return f"ran model {n} times, {duration:.2f} total, {duration_per:.2f} per run"


@app.callback(
    Output("bar-graph", "figure"),
    Output("time-graph", "figure"),
    Output("scatter-graph", "figure"),
    Output("eff-graph", "figure"),
    Input("element-input", "value"),
    Input("agg-input", "value"),
    Input("scenario-input", "value"),
    Input("response-input", "value")
)
def update_graphs(element_pk, agg_value, scenario_pks, response_pks):
    baseline_response_pk = 1
    scenario_pks.sort()
    response_pks.sort()
    response2color = {response_pk: color
                      for response_pk, color in zip(response_pks[1:], itertools.cycle(DEFAULT_PLOTLY_COLORS))}
    response2color[baseline_response_pk] = "black"
    print(response2color)
    DASHES = ["solid", "dot", "dash", "longdash", "dashdot", "longdashdot"]
    scenario2dash = {scenario_pk: dash for scenario_pk, dash in zip(scenario_pks, DASHES)}
    element = Element.objects.get(pk=element_pk)

    response_pks_filter = response_pks.copy()
    if baseline_response_pk not in response_pks:
        response_pks_filter.append(baseline_response_pk)

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

    df_agg = df.groupby([
        "responseoption_id", "scenario_id", "responseoption__name", "scenario__name"
    ])["value"]
    period = (df["date"].iloc[1] - df["date"].iloc[0]).days

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
    time_fig.update_yaxes(title_text=f"{element.label} ({element.unit})")


    # scatter graph
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

    scatter_fig = go.Figure(layout=dict(template="simple_white"))
    show_response_legend = True
    for scenario_pk in scenario_pks:
        dff_agg = df_agg.loc[df_cost_agg["scenario_id"] == scenario_pk]
        dff_agg.loc[:, "cost"] = df_cost_agg.loc[df_cost_agg["scenario_id"] == scenario_pk]["value"]
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
    scatter_fig.update_xaxes(title_text="Coûts totaux CICR (FCFA)")
    scatter_fig.update_yaxes(title_text=f"{element.label} {agg_text} ({agg_unit})")

    # effciency graph
    eff_fig = go.Figure(layout=dict(template="simple_white"))
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
    y_title = "1" if agg_unit == "1000 FCFA" else f"{agg_unit} / {divider_text} FCFA"
    eff_fig.update_yaxes(title_text=y_title)
    eff_fig.update_xaxes(ticklen=0, showline=False, tickfont_size=14)
    eff_fig.add_hline(y=0, line_width=1, line_color="black", opacity=1)


    return bar_fig, time_fig, scatter_fig, eff_fig

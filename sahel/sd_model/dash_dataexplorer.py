import time

import plotly.colors
from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

import pandas as pd
import json
import plotly.graph_objects as go

from sahel.models import Source, Variable, MeasuredDataPoint, SP_NAMES, ForecastedDataPoint

DEFAULT_SOURCE_PK = 1

app = DjangoDash("dataexplorer", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(fluid=True, style={"background-color": "#f8f9fc"}, children=[
    html.P(id='init', hidden=True),
    dbc.Row([
        dbc.Col([
            html.H4(id="simple-title", className="my-4", children="Explorateur de données"),
        ])
    ]),
    dbc.Row([
        dbc.Col(width=3, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(children=[
                    dbc.InputGroup(className="mb-2", children=[
                        dbc.InputGroupAddon("Source", addon_type="prepend"),
                        dbc.Select(id=(SOURCE_INPUT := "cereal-input")),
                    ]),
                    dbc.InputGroup(className="mb-2", children=[
                        dbc.InputGroupAddon("Élément", addon_type="prepend"),
                        dbc.Select(id=(VARIABLE_INPUT := "variable-input")),
                    ]),
                    dbc.InputGroup(className="mb-2", children=[
                        dbc.InputGroupAddon("Pays", addon_type="prepend"),
                        dbc.Select(id=(ADMIN0_INPUT := "admin0-input")),
                    ]),
                    dbc.InputGroup(className="mb-3", children=[
                        dbc.InputGroupAddon("Niveau", addon_type="prepend"),
                        dbc.Select(id=(AVG_INPUT := "avg-input")),
                    ]),
                    dbc.Checklist(
                        id=(FORECAST_INPUT := "forecast-input"),
                        className="mb-2",
                        options=[{"label": "Montrer prévisions", "value": (SHOW_FORECAST := "show-forecast")}],
                        value=[],
                        switch=True,
                    )
                ]),
            ]),
        ]),
        dbc.Col(width=9, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(children=[
                    dcc.Loading(dcc.Graph(id=(LINE_GRAPH := "line-graph"), style={"height": "700px"}))
                ])
            ])
        ]),
    ]),
    html.Div(id="readouts", hidden=True, children=[
        dbc.Select(id=(AVG_BY_READOUT := 'avg-by-readout')),
    ])
])


@app.callback(
    Output(SOURCE_INPUT, "options"),
    Output(SOURCE_INPUT, "value"),
    Input("init", "children")
)
def populate_initial(_):
    return (
        [
            {"value": source.get("id"), "label": source.get("title")}
            for source in Source.objects.all().values()
        ],
        DEFAULT_SOURCE_PK
    )


@app.callback(
    Output(VARIABLE_INPUT, "options"),
    Output(VARIABLE_INPUT, "value"),
    Output(ADMIN0_INPUT, "options"),
    Output(ADMIN0_INPUT, "value"),
    Output(AVG_BY_READOUT, "options"),
    Input(SOURCE_INPUT, "value")
)
def populate_variable_admin0_input(source_pk):
    start = time.time()
    df = pd.DataFrame(MeasuredDataPoint.objects.filter(source_id=source_pk).values())
    print(f"initial mdp hit took {time.time() - start}")
    if df.empty:
        return [], None, [], None, []
    variables = Variable.objects.filter(pk__in=df['element_id'].unique()).values()
    admin0s = df['admin0'].unique()
    admin_disabled = {
        'Pays': False,
        'admin1': None in df['admin1'].unique(),
        'admin2': None in df['admin2'].unique(),
        'Marché': None in df['market'].unique(),
    }
    return (
        [{"value": variable.get("id"), "label": variable.get("label")} for variable in variables],
        variables[0].get("id"),
        [{"value": admin0, "label": admin0} for admin0 in admin0s],
        admin0s[0],
        [{"value": admin, "label": admin, "disabled": disabled} for admin, disabled in admin_disabled.items()],
    )


@app.callback(
    Output(AVG_INPUT, "options"),
    Output(AVG_INPUT, "value"),
    Input(ADMIN0_INPUT, "value"),
    Input(AVG_BY_READOUT, "options"),
)
def populate_avg_by(admin0, options):
    for option in options:
        label = SP_NAMES.get(admin0).get(option.get("value"))
        if label is not None:
            option.update({"label": label})
    return options, "admin1"


@app.callback(
    Output(FORECAST_INPUT, "options"),
    Output(FORECAST_INPUT, "value"),
    Input(AVG_INPUT, "value"),
    State(FORECAST_INPUT, "options"),
    State(FORECAST_INPUT, "value"),
)
def populate_showforecast(avg_by, options, value):
    if avg_by in ["Pays", "admin1"]:
        options[0].update({"disabled": False})
    else:
        options[0].update({"disabled": True})
        value = []
    return options, value


@app.callback(
    Output(LINE_GRAPH, "figure"),
    Input(VARIABLE_INPUT, "value"),
    Input(ADMIN0_INPUT, "value"),
    Input(AVG_INPUT, "value"),
    Input(FORECAST_INPUT, "value"),
    State(SOURCE_INPUT, "value"),
)
def update_graph(variable_pk, admin0, avg_by, forecast_input, source_pk):
    fig = go.Figure(layout=dict(template="simple_white"))
    show_forecast = SHOW_FORECAST in forecast_input
    if None in [variable_pk, admin0, avg_by, source_pk]:
        fig.layout.annotations = [dict(
            text="Aucune donnée quantitative",
            opacity=0.1,
            font=dict(color="black", size=30),
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )]
        return fig
    colors = iter(plotly.colors.DEFAULT_PLOTLY_COLORS)
    avg_by_local = SP_NAMES.get(admin0).get(avg_by, avg_by)
    variable = Variable.objects.get(pk=variable_pk)
    start = time.time()
    df = pd.DataFrame(MeasuredDataPoint.objects.filter(
        source_id=source_pk, element_id=variable_pk, admin0=admin0
    ).values())
    print(f"mdp hit took {time.time() - start}")
    if show_forecast:
        df_f = pd.DataFrame(ForecastedDataPoint.objects.filter(element_id=variable_pk, admin0=admin0).values())
    moyenne = "" if avg_by == "Marché" else "moyenne "
    fig.update_layout(
        title_text=f"{variable.label}<br><sup>{admin0} - {moyenne}par {avg_by_local.lower()}</sup>",
        legend_title_text=avg_by_local,
        showlegend=True,
    )
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text=f"Valeur ({variable.unit.replace('LCY', SP_NAMES.get(admin0).get('currency'))})")
    if avg_by == 'Pays':
        df = df.groupby("date").mean().reset_index()
        color = next(colors)
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["value"],
            name=admin0,
            mode="lines",
            line_color=color,
        ))
        if show_forecast:
            df_f = df_f.groupby("date").mean().reset_index()
            fig.add_trace(go.Scatter(
                x=df_f["date"],
                y=df_f["value"],
                name=f"{admin0} - prévisé",
                showlegend=False,
                mode="lines",
                line={"color": color, "dash": "dash"},
            ))
    else:
        admin1s = df['admin1'].unique()
        for admin1 in admin1s:
            color = next(colors)
            dff = df[df['admin1'] == admin1]
            if show_forecast:
                dff_f = df_f[df_f['admin1'] == admin1]
            if avg_by == 'admin1':
                dff = dff.groupby("date").mean().reset_index()
                fig.add_trace(go.Scatter(
                    x=dff["date"],
                    y=dff["value"],
                    name=admin1,
                    mode="lines",
                    line_color=color,
                ))
                if show_forecast:
                    dff_f = dff_f.groupby("date").mean().reset_index()
                    fig.add_trace(go.Scatter(
                        x=dff_f["date"],
                        y=dff_f["value"],
                        name=f"{admin1} - prévisé",
                        mode="lines",
                        showlegend=False,
                        line={"color": color, "dash": "dash"},
                    ))
            else:
                admin2s = dff['admin2'].unique()
                for admin2 in admin2s:
                    dfff = dff[dff['admin2'] == admin2]
                    if avg_by == 'admin2':
                        dfff = dfff.groupby("date").mean().reset_index()
                        fig.add_trace(go.Scatter(
                            x=dfff["date"],
                            y=dfff["value"],
                            name=admin2,
                            mode="lines",
                            legendgroup=admin1,
                            legendgrouptitle_text=admin1,
                        ))
                    else:
                        markets = dfff['market'].unique()
                        for market in markets:
                            dffff = dfff[dfff['market'] == market]
                            fig.add_trace(go.Scatter(
                                x=dffff['date'],
                                y=dffff['value'],
                                name=market,
                                mode="lines",
                                legendgroup=admin2,
                                legendgrouptitle_text=admin2,
                            ))
    return fig
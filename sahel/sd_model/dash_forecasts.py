from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Variable, ResponseConstantValue, ADMIN0S

from .forecasting import forecast_element
from .model_operations import timer
import time

import plotly.graph_objects as go
import plotly
from plotly.subplots import make_subplots
import pandas as pd

# TODO: vastly simplify, remove all controls and literally just show data (forecasting should be done automatically
#  or triggered by admin somehow, not here)

default_colors = plotly.colors.DEFAULT_PLOTLY_COLORS

app = DjangoDash("forecasts", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(style={"background-color": "#f8f9fc"}, fluid=True, children=[
    html.Div(id='init'),
    dbc.Row([
        dbc.Col([
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardHeader("Montrer prévision"),
                dbc.CardBody([
                    dbc.Select(id=(ADMIN0_INPUT := 'admin0-input')),
                    dbc.Select(id=(ELEMENT_INPUT := "element-input")),
                    # html.Hr(),
                    # html.H6("SARIMA parameters"),
                    # dbc.InputGroup([
                    #     dbc.Input(id=f"{letter}-input", value=0)
                    #     for letter in "pdq"
                    # ]),
                    # dbc.InputGroup([
                    #     dbc.Input(id=f"{letter}-input", value=0)
                    #     for letter in "PDQm"
                    # ]),
                    # dbc.Button("Re-forecast", id="forecast-test-submit", color="warning", disabled=True),
                    # html.Hr(),
                    # html.H5("Préviser avec les défauts"),
                    # dbc.Button("Préviser", id="forecast-submit", disabled=False),
                    # dbc.Button("Préviser TOUS", id="forecast-all-submit", color="danger", disabled=True),
                ]),
            ])
        ], width=2),
        dbc.Col(width=10, children=[
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardHeader("Prévision"),
                dbc.CardBody([
                    dcc.Loading(dcc.Graph(id="element-graph"))
                ])
            ]),
        ])
    ]),
    dcc.Loading(html.Div(id="forecast-readout")),
    dcc.Loading(html.Div(id="forecast-test-readout")),
    dcc.Loading(html.Div(id="forecast-all-readout")),
])


@app.callback(
    Output(ADMIN0_INPUT, 'options'),
    Output(ADMIN0_INPUT, 'value'),
    Output(ELEMENT_INPUT, "options"),
    Output(ELEMENT_INPUT, 'value'),
    Input('init', 'children'),
)
def init(_):
    variables = Variable.objects.filter(sd_type="Input").exclude(measureddatapoints=None)
    return (
        [{'value': adm0, 'label': adm0} for adm0 in ADMIN0S],
        'Mauritanie',
        [{"label": variable.label, "value": variable.pk} for variable in variables],
        42,
    )


@app.callback(
    Output("element-graph", "figure"),
    Input(ELEMENT_INPUT, "value"),
    Input(ADMIN0_INPUT, 'value'),
    Input("forecast-readout", "children"),
    Input("forecast-test-readout", "children"),
)
def update_graph(element_pk, adm0, *_):
    fig = go.Figure()
    fig.update_layout(template="simple_white", margin=dict(l=0, r=0, b=0, t=0))

    element = Variable.objects.get(pk=element_pk)

    df = pd.DataFrame(element.measureddatapoints.filter(admin0=adm0).values())
    df["forecasted"] = False
    df_forecast = pd.DataFrame(element.forecasteddatapoints.filter(admin0=adm0).values())
    df_forecast["forecasted"] = True
    df = pd.concat([df, df_forecast], ignore_index=True)

    admin1s = df["admin1"].unique()

    if len(admin1s) > 1:
        dff = df.groupby(["date", "forecasted"]).mean().reset_index()
        fig.add_trace(go.Scatter(
            x=dff[~dff["forecasted"]]["date"], y=dff[~dff["forecasted"]]["value"], name="Mesuré",
            line=dict(color="black", width=2), legendgroup="AVG", legendgrouptitle_text="AVG"))
        fig.add_trace(go.Scatter(
            x=dff[dff["forecasted"]]["date"], y=dff[dff["forecasted"]]["value"], name="Prévisé",
            line=dict(color="black", width=2, dash="dash"), legendgroup="AVG"))

    for admin1, color in zip(admin1s, default_colors):
        if admin1 is not None:
            dff = df[df["admin1"] == admin1]
        else:
            dff = df
        dff = dff.groupby(["date", "forecasted"]).mean().reset_index()
        fig.add_trace(go.Scatter(
            x=dff[~dff["forecasted"]]["date"],
            y=dff[~dff["forecasted"]]["value"],
            name="Mesuré",
            line=dict(color=color, width=1),
            legendgroup=admin1,
            legendgrouptitle_text=admin1
        ))
        x_forecast = list(dff[dff["forecasted"]]["date"])
        fig.add_trace(go.Scatter(
            x=x_forecast,
            y=dff[dff["forecasted"]]["value"],
            name="Prévisé",
            line=dict(color=color, dash="dash", width=1),
            legendgroup=admin1
        ))
        fig.add_trace(go.Scatter(
            x=x_forecast+x_forecast[::-1], # x, then x reversed
            y=list(dff[dff["forecasted"]]["upper_bound"])+list(dff[dff["forecasted"]]["lower_bound"])[::-1], # upper, then lower reversed
            fill='toself',
            line=dict(color=color, width=0),
            opacity=0.3,
            hoverinfo="skip",
            showlegend=False
        ))

    return fig


# @app.callback(
#     Output("forecast-test-readout", "children"),
#     Input("forecast-test-submit", "n_clicks"),
#     State("element-input", "value"),
#     [State(f"{letter}-input", "value") for letter in "pdqPDQm"],
# )
# @timer
# def update_test_forecast(n_clicks, element_pk, p, d, q, P, D, Q, m):
#     if n_clicks is None: raise PreventUpdate
#     sarima_params = {"p": p, "d": d, "q": q, "P": P, "D": D, "Q": Q, "m": m}
#     forecast_element(element_pk, sarima_params=sarima_params)
#     return f"forecasted {element_pk} with test params"


# @app.callback(
#     Output("forecast-readout", "children"),
#     Input("forecast-submit", "n_clicks"),
#     State("element-input", "value"),
# )
# def update_forecast(n_clicks, element_pk):
#     if n_clicks is None: raise PreventUpdate
#     forecast_element(element_pk)
#     return f"forecasted {element_pk} with default"


# @app.callback(
#     Output("forecast-all-readout", "children"),
#     Input("forecast-all-submit", "n_clicks"),
# )
# def update_forecast_all(n_clicks):
#     if n_clicks is None:
#         raise PreventUpdate
#     start = time.time()
#     for element in Variable.objects.filter(sd_type="Input").exclude(measureddatapoints=None):
#         forecast_element(element.pk)
#     return f"forecasted all, took {time.time() - start} s"
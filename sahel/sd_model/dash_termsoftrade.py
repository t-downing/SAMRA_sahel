import time

from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Element, Scenario, MeasuredDataPoint
from sahel.sd_model.model_operations import run_model

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
import itertools
import pandas as pd

tooltip_style = {"text-decoration-line": "underline", "text-decoration-style": "dotted"}

app = DjangoDash("termsoftrade", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(fluid=True, style={"background-color": "#f8f9fc"}, children=[
    dbc.Row([
        dbc.Col([
            html.H4(id="simple-title", className="mb-4", children="Simple: prix contre prix"),
            html.P("Combien de kg d'une céréale peut-on acheter si on vend une tête de bétail ?")
        ])
    ]),
    dbc.Row([
        dbc.Col(width=3, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(children=[
                    dbc.InputGroup(className="mb-2", children=[
                        dbc.InputGroupAddon("Céréale", addon_type="prepend"),
                        dbc.Select(id="cereal-input"),
                    ]),
                    html.P(className="mb-2 text-center", children="contre"),
                    dbc.InputGroup(children=[
                        dbc.InputGroupAddon("Bétail", addon_type="prepend"),
                        dbc.Select(id="livestock-input"),
                    ]),
                ]),
            ]),
        ]),
        dbc.Col(width=9, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(children=[
                    dcc.Loading(dcc.Graph(id="simple-graph", style={"height": "600px"}))
                ])
            ])
        ])
    ]),
    dbc.Row([
        dbc.Col([
            html.H4(id="simple-title", className="mb-4 mt-4", children="Complexe: panier alimentaire contre cheptel"),
            html.P("Pour combien de journées peut-on acheter le panier alimentaire du ménage si on vend tout le cheptel ?")
        ])
    ]),
    dbc.Row([
        dbc.Col(width=3, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(children=[
                    dbc.InputGroup(className="mb-3", children=[
                        dbc.InputGroupAddon("Taille de ménage", addon_type="prepend"),
                        dbc.Input(id="headcount-input", type="number", value=5),
                    ]),

                    html.H6("Composition du panier alimentaire:"),
                    dbc.Table(className="mb-4", size="sm", style={"width": "100%"},
                              children=[html.Thead(style={"display": "block", "width": "100%"}, children=html.Tr([
                                  html.Th(id="commodity-head", style={"width": "50%"}, children="Aliment"),
                                  html.Th(id="kcal-head", style={"width": "40%"}, children="% kcal"),
                                  dbc.Tooltip("Fraction des calories totales consommées par le ménage qui proviennent de cet aliment",
                                              target="kcal-head"),
                                  html.Th(id="kg-head", children="kg"),
                                  dbc.Tooltip("Calculé: quantité d'aliment réquis pour satisfaire fraction de calories (présumé 2100 kcal par personne)",
                                              target="kg-head")
                              ])),
                        html.Tbody(id="basket-inputs", style={"max-height": "180px", "overflow-y": "scroll", "font-size": "small", "display": "block"}),]
                    ),

                    html.H6("Composition du cheptel:"),
                    dbc.Table(className="mb-0", size="sm", children=html.Thead(html.Tr([html.Th("Espèce"), html.Th("Nombre")]))),
                    html.Div(style={"max-height": "180px", "overflow-y": "scroll"}, children=dbc.Table(size="sm", children=[
                        html.Tbody(id="herd-inputs"),
                    ]),),
                ]),
            ]),
        ]),
        dbc.Col(width=9, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(children=[
                    dcc.Loading(dcc.Graph(id="complex-graph", style={"height": "600px"})),
                ])
            ])
        ])
    ]),
])


@app.callback(
    Output("livestock-input", "options"),
    Output("livestock-input", "value"),
    Output("cereal-input", "options"),
    Output("cereal-input", "value"),
    Output("basket-inputs", "children"),
    Output("herd-inputs", "children"),
    Input("simple-title", "children"),
)
def populate_initial(_):
    livestock_pks = [62, 63, 42]
    livestock_elements = Element.objects.filter(pk__in=livestock_pks)
    livestock_options = [{"value": element.pk,
                          "label": element.label.removeprefix("Prix de ")
                              .capitalize()}
                         for element in livestock_elements]

    cereal_pks = [53, 54, 55, 56, 57, 58, 59, 60, 61, 70, 130, 131]
    cereal_elements = Element.objects.filter(pk__in=cereal_pks)
    cereal_options = [{"value": element.pk,
                       "label": element.label.removeprefix("Prix de ").removeprefix("Prix du ")
                           .removeprefix("Prix d'").capitalize()}
                      for element in cereal_elements]

    basket_inputs = []
    for cereal_option in cereal_options:
        value = 100 if cereal_option.get("value") == 53 else None
        basket_inputs.append(
            html.Tr([
                html.Td(cereal_option.get("label")),
                html.Td(dbc.Input(
                    id={"type": "cereal-input", "index": cereal_option.get('value')}, type="number", size="sm",
                    value=value
                )),
                html.Td(id={"type": "cereal-kg", "index": cereal_option.get('value')})
            ]),
        )

    herd_inputs =[]
    for livestock_option in livestock_options:
        value = 5 if livestock_option.get("value") in [62, 63] else None
        herd_inputs.append(
            html.Tr([
                html.Td(livestock_option.get("label")),
                html.Td(dbc.Input(id={"type": "livestock-input", "index": livestock_option.get('value')}, type="number",
                                  size="sm", value=value)),
            ]),
        )

    return livestock_options, livestock_pks[0], cereal_options, cereal_pks[-1], basket_inputs, herd_inputs


@app.callback(
    Output("complex-graph", "figure"),
    Input("headcount-input", "value"),
    Input({"type": "cereal-input", "index": ALL}, "value"),
    Input({"type": "cereal-input", "index": ALL}, "id"),
    Input({"type": "livestock-input", "index": ALL}, "value"),
    Input({"type": "livestock-input", "index": ALL}, "id"),
)
def update_complex_graph(headcount, cereal_values, cereal_ids, livestock_values, livestock_ids):
    kcal_total = 2100
    cereal_pks = []
    cereal_pk_values = []
    for value, id in zip(cereal_values, cereal_ids):
        if value is None or value <= 0:
            continue
        cereal_pks.append(id.get("index"))
        cereal_pk_values.append((id.get("index"), value))

    livestock_pks = []
    livestock_pk_values =[]
    for value, id in zip(livestock_values, livestock_ids):
        if value is None or value <= 0:
            continue
        livestock_pks.append(id.get("index"))
        livestock_pk_values.append((id.get("index"), value))

    df = pd.DataFrame(MeasuredDataPoint.objects.filter(element_id__in=cereal_pks+livestock_pks).values())
    if df.empty:
        raise PreventUpdate
    df = df.pivot(index=["date", "admin1", "admin2", "market"], columns="element_id", values="value").reset_index()
    df = df.dropna()

    df["meb_cost"] = 0
    for cereal_pk_value in cereal_pk_values:
        element = Element.objects.get(pk=cereal_pk_value[0])
        df["meb_cost"] += df[int(cereal_pk_value[0])] * cereal_pk_value[1] / element.kcal_per_kg / 100 * headcount * kcal_total

    df["herd_value"] = 0
    for livestock_pk_value in livestock_pk_values:
        df["herd_value"] += df[int(livestock_pk_value[0])] * livestock_pk_value[1]

    df["days_afford"] = df["herd_value"] / df["meb_cost"]

    fig = go.Figure(layout=dict(template="simple_white"))
    for admin1 in df["admin1"].unique():
        dff = df[df["admin1"] == admin1]
        dff = dff.groupby(["date"]).mean().reset_index()
        fig.add_trace(go.Scatter(
            x=dff["date"],
            y=dff["days_afford"],
            name=admin1,
            mode="lines",
            text=dff.apply(
                lambda row: f"Panier alimentaire: {round(row['meb_cost'])} FCFA / jour<br>"
                            f"Valeur total de cheptel: {round(row['herd_value'])} FCFA",
                axis=1
            ),
            hovertemplate="%{text}"
        ))

    fig.update_yaxes(title_text="journées")
    fig.update_layout(
        title_text=f"Journées de survie avec vente complète de cheptel",
        legend_title_text="Région"
    )

    return fig


@app.callback(
    Output({"type": "cereal-kg", "index": MATCH}, "children"),
    Input({"type": "cereal-input", "index": MATCH}, "value"),
    Input("headcount-input", "value"),
    Input({"type": "cereal-input", "index": MATCH}, "id"),
)
def calculate_kgs(frac_kcal, headcount, id):
    if frac_kcal is None:
        return None
    element = Element.objects.get(pk=id.get("index"))
    return round(frac_kcal * headcount * 2100 / element.kcal_per_kg / 100, 2)


@app.callback(
    Output("simple-graph", "figure"),
    Input("livestock-input", "value"),
    Input("cereal-input", "value"),
)
def update_simple_graph(livestock_pk, cereal_pk):
    df_m = pd.DataFrame(MeasuredDataPoint.objects.filter(element_id__in=[livestock_pk, cereal_pk]).values())
    df_m = df_m.pivot(index=["date", "admin1", "admin2", "market"], columns="element_id", values="value").reset_index()
    df = df_m

    df["terms"] = df_m[int(livestock_pk)] / df_m[int(cereal_pk)]
    df = df.dropna()

    cereal_element = Element.objects.get(pk=cereal_pk)
    cereal_name = cereal_element.label.removeprefix("Prix de ").removeprefix("Prix du ").removeprefix("Prix d'")
    cereal_unit = cereal_element.unit.removeprefix("FCFA / ")

    livestock_element = Element.objects.get(pk=livestock_pk)
    livestock_name = livestock_element.label.removeprefix("Prix de ")

    fig = go.Figure(layout=dict(template="simple_white"))
    for admin1 in df["admin1"].unique():
        dff = df[df["admin1"] == admin1]
        dff = dff.groupby(["date"]).mean().reset_index()
        fig.add_trace(go.Scatter(
            x=dff["date"],
            y=dff["terms"],
            name=admin1,
            mode="lines",
            text=dff.apply(
                lambda row: f"{cereal_name.capitalize()}: {round(row[int(cereal_pk)])} FCFA / {cereal_unit}<br>"
                            f"{livestock_name.capitalize()}: {round(row[int(livestock_pk)])} FCFA / tête",
                axis=1
            ),
            hovertemplate="%{text}",
        ))

    fig.update_yaxes(title_text=f"{cereal_unit} {cereal_name} / tête {livestock_name}")
    fig.update_layout(
        title_text=f"Termes d'échange <b>{cereal_name}</b> / <b>{livestock_name}</b>",
        legend_title_text="Région"
    )

    return fig


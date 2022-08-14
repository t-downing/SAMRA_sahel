from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Element, ConstantValue, PulseValue

from sahel.sd_model.model_operations import run_model, timer

import plotly.graph_objects as go
import plotly
from plotly.subplots import make_subplots
import pandas as pd

default_colors = plotly.colors.DEFAULT_PLOTLY_COLORS

ROWSTYLE = {"margin-bottom": "10px"}

app = DjangoDash("response_builder", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(style={"background-color": "#f8f9fc"}, fluid=True, children=[
    dbc.Row([
        dbc.Col([
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardHeader("Construire une réponse"),
                dbc.CardBody([
                    dbc.InputGroup([
                        dbc.InputGroupText("Modifier une réponse"),
                        dbc.Select(id="build-response-input"),
                    ]),
                    dcc.Loading(html.Div(id="response-constants")),
                    html.P("OU", style={"margin": "20px", "text-align": "center"}),
                    dbc.InputGroup([
                        dbc.InputGroupText("Créer une nouvelle réponse"),
                        dbc.Input(id="create-response-input", placeholder="Nom de réponse"),
                        dbc.Button("Saisir", id="create-response-submit", color="success"),
                    ]),
                ]),
            ]),
        ], width=12),
    ]),
    html.Div(id="constantvalue-deleted-readout"),
    html.Div(id="constantvalue-changed-readout"),
    html.Div(id="pulse-deleted-readout"),
    html.Div(id="pulse-changed-readout"),
    html.Div(id="constantvalue-added-readout"),
    html.Div(id="response-added-readout"),
])


@app.callback(
    Output("build-response-input", "options"),
    Output("build-response-input", "value"),
    Input("response-added-readout", "children")
)
def populate_initial(_):
    response_options = [{"label": response.name, "value": response.pk} for response in ResponseOption.objects.all()]
    response_value = [1, 2]
    print(response_value[1])
    return response_options, response_value[1]


@app.callback(
    Output("response-added-readout", "children"),
    Input("create-response-submit", "n_clicks"),
    State("create-response-input", "value"),
)
@timer
def create_response(_, value):
    if value is None:
        raise PreventUpdate
    response = ResponseOption(name=value)
    response.save()
    return f"added {response}"


@app.callback(
    Output("constantvalue-added-readout", "children"),
    Input("constantvalue-submit", "n_clicks"),
    State("constantvalue-element-input", "value"),
    State("constantvalue-value-input", "value"),
    State("constantvalue-date-input", "date"),
    State("build-response-input", "value"),
)
def create_constantvalue(n_clicks, element_pk, value, date, response_pk):
    if None in [n_clicks, element_pk, value, response_pk]:
        raise PreventUpdate
    element = Element.objects.get(pk=element_pk)
    if element.sd_type == "Constant":
        ConstantValue(responseoption_id=response_pk, element_id=element_pk, value=value).save()
    elif element.sd_type == "Pulse Input":
        print(date)
        PulseValue(responseoption_id=response_pk, element_id=element_pk, value=value, startdate=date).save()
    run_model(responseoption_pk=response_pk)
    return f"created {element.sd_type} value with value {value}"


@app.callback(
    Output("constantvalue-deleted-readout", "children"),
    Input({"type": "constantvalue-delete", "index": ALL}, "n_clicks"),
    State({"type": "constantvalue-delete", "index": ALL}, "id"),
)
def delete_constantvalue(n_clicks, ids):
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            constantvalue = ConstantValue.objects.get(pk=id.get("index"))
            constantvalue.delete()
            run_model(responseoption_pk=constantvalue.responseoption.pk)
            return f"{id} deleted, RERUN MODEL"
    raise PreventUpdate


@app.callback(
    Output("pulse-deleted-readout", "children"),
    Input({"type": "pulse-delete", "index": ALL}, "n_clicks"),
    State({"type": "pulse-delete", "index": ALL}, "id"),
)
def delete_pulse(n_clicks, ids):
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            pulsevalue = PulseValue.objects.get(pk=id.get("index"))
            pulsevalue.delete()
            run_model(responseoption_pk=pulsevalue.responseoption.pk)
            return f"{id} deleted, RERUN MODEL"
    raise PreventUpdate


@app.callback(
    Output("constantvalue-changed-readout", "children"),
    Input({"type": "constantvalue-change", "index": ALL}, "n_clicks"),
    State({"type": "constantvalue-change", "index": ALL}, "id"),
    State({"type": "constantvalue-change-input", "index": ALL}, "value"),
)
def change_constantvalue(n_clicks, ids, values):
    for n_click, id, value in zip(n_clicks, ids, values):
        if n_click is not None:
            if value is not None:
                constantvalue = ConstantValue.objects.get(pk=id.get("index"))
                constantvalue.value = value
                constantvalue.save()
                run_model(responseoption_pk=constantvalue.responseoption.pk)
                return f"{constantvalue} changed"
    raise PreventUpdate


@app.callback(
    Output("pulse-changed-readout", "children"),
    Input({"type": "pulse-change", "index": ALL}, "n_clicks"),
    State({"type": "pulse-change", "index": ALL}, "id"),
    State({"type": "pulse-change-input", "index": ALL}, "value"),
)
def change_pulsevalue(n_clicks, ids, values):
    for n_click, id, value in zip(n_clicks, ids, values):
        if n_click is not None:
            if value is not None:
                pulsevalue = PulseValue.objects.get(pk=id.get("index"))
                pulsevalue.value = value
                pulsevalue.save()
                run_model(responseoption_pk=pulsevalue.responseoption.pk)
                return f"{pulsevalue} changed"
    raise PreventUpdate


@app.callback(
    Output("response-constants", "children"),
    Input("build-response-input", "value"),
    Input("constantvalue-deleted-readout", "children"),
    Input("constantvalue-added-readout", "children"),
    Input("constantvalue-changed-readout", "children"),
    Input("pulse-deleted-readout", "children"),
    Input("pulse-changed-readout", "children"),
)
def build_response(response_pk, *_):
    if response_pk is None:
        raise PreventUpdate
    response = ResponseOption.objects.get(pk=response_pk)
    table_header = [html.Thead(html.Tr([
        html.Th("Élément"), html.Th("Valeur"), html.Th("Unité"), html.Th("Date"), html.Th()
    ]))]
    table_rows = []
    for constantvalue in response.constantvalues.all():
        table_rows.append(html.Tr([
            html.Td(constantvalue.element.label),
            html.Td(dbc.InputGroup([
                dbc.Input(value=constantvalue.value,
                          id={"type": "constantvalue-change-input", "index": constantvalue.pk}),
                dbc.Button("Changer", id={"type": "constantvalue-change", "index": constantvalue.pk}),
            ], size="sm")),
            html.Td(constantvalue.element.unit),
            html.Td("N/A", style={"color": "gray"}),
            html.Td(dbc.Button("Supprimer", id={"type": "constantvalue-delete", "index": constantvalue.pk}, size="sm",
                               color="danger", outline=True)),
        ]))

    for pulsevalue in response.pulsevalues.all():
        table_rows.append(html.Tr([
            html.Td(pulsevalue.element.label),
            html.Td(dbc.InputGroup([
                dbc.Input(value=pulsevalue.value,
                          id={"type": "pulse-change-input", "index": pulsevalue.pk}),
                dbc.Button("Changer", id={"type": "pulse-change", "index": pulsevalue.pk}),
            ], size="sm")),
            html.Td(pulsevalue.element.unit),
            html.Td(pulsevalue.startdate),
            html.Td(dbc.Button("Supprimer", id={"type": "pulse-delete", "index": pulsevalue.pk}, size="sm",
                               color="danger", outline=True)),
        ]))

    table_rows.append(html.Tr([
        html.Td(dcc.Dropdown(id="constantvalue-element-input", placeholder="Ajouter un élément",
                             options=[{"label": element.label, "value": element.pk}
                                      for element in Element.objects.filter(sd_type__in=["Constant", "Pulse Input"])])),
        html.Td(dbc.Input(id="constantvalue-value-input")),
        html.Td(id="constantvalue-unit-input"),
        html.Td(dcc.DatePickerSingle(id="constantvalue-date-input")),
        html.Td(dbc.Button("Saisir", id="constantvalue-submit", size="sm"))
    ]))

    return dbc.Table(table_header + [html.Tbody(table_rows)])


@app.callback(
    Output("constantvalue-unit-input", "children"),
    Input("constantvalue-element-input", "value")
)
def show_constantvalue_unit(element_pk):
    if element_pk is None:
        raise PreventUpdate
    return Element.objects.get(pk=element_pk).unit


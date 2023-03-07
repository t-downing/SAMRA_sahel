from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, Variable, ResponseConstantValue, PulseValue, ADMIN0S, CURRENCY

from sahel.sd_model.model_operations import run_model, timer

import plotly.graph_objects as go
import plotly
from plotly.subplots import make_subplots
import pandas as pd

default_colors = plotly.colors.DEFAULT_PLOTLY_COLORS

ROWSTYLE = {"margin-bottom": "10px"}

app = DjangoDash("response_builder", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(style={"background-color": "#f8f9fc"}, fluid=True, children=[
    html.Div(id='init', hidden=True),
    dbc.Row([
        dbc.Col([
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardHeader("Construire une réponse"),
                dbc.CardBody([
                    dbc.InputGroup([
                        dbc.InputGroupAddon("Modifier une réponse", addon_type="prepend"),
                        dbc.Select(id="build-response-input"),
                    ]),
                    dbc.InputGroup([
                        dbc.InputGroupAddon("Définir les valeurs pour :", addon_type="prepend"),
                        dbc.Select(id=(ADMIN0_INPUT := 'admin0-input')),
                    ]),
                    dcc.Loading(html.Div(id="response-constants")),
                    html.P("OU", style={"margin": "20px", "text-align": "center"}),
                    dbc.InputGroup([
                        dbc.InputGroupAddon("Créer une nouvelle réponse", addon_type="prepend"),
                        dbc.Input(id="create-response-input", placeholder="Nom de réponse"),
                        dbc.InputGroupAddon(dbc.Button("Saisir", id="create-response-submit", color="success"), addon_type="append"),
                    ]),
                ]),
            ]),
        ], width=12),
    ]),
    html.Div(id="value-deleted-readout"),
    html.Div(id="value-changed-readout"),
    html.Div(id="pulse-deleted-readout"),
    html.Div(id="pulse-changed-readout"),
    html.Div(id="value-added-readout"),
    html.Div(id="response-added-readout", hidden=True),
])


@app.callback(
    Output(ADMIN0_INPUT, 'options'),
    Output(ADMIN0_INPUT, 'value'),
    Input('init', 'children'),
)
@timer
def init(_):
    return (
        [{'label': adm0, 'value': adm0} for adm0 in ADMIN0S],
        'Mauritanie'
    )


# TODO: find a way to connect this to the responseoption creation
@app.callback(
    Output("build-response-input", "options"),
    Output("build-response-input", "value"),
    # Input("response-added-readout", "children")
    Input('init', 'children'),
)
@timer
def populate_responseoptions(new_response_pk):
    if new_response_pk is None:
        new_response_pk = 2
    return (
        [{"label": response.name, "value": response.pk} for response in ResponseOption.objects.all()],
        new_response_pk,
    )


@app.callback(
    Output("response-added-readout", "children"),
    Input("create-response-submit", "n_clicks"),
    State("create-response-input", "value"),
)
@timer
def create_response(n_clicks, value):
    if n_clicks is None:
        raise PreventUpdate
    response = ResponseOption(name=value)
    response.save()
    return response.pk


# NOTE: for some reason, cannot put @timer on this function (it throws up Dash exceptions saying the callback doesn't
# match or something)
@app.callback(
    Output("value-added-readout", "children"),
    Input("value-submit", "n_clicks"),
    State("value-element-input", "value"),
    State("value-value-input", "value"),
    State("value-date-input", "date"),
    State("build-response-input", "value"),
    State(ADMIN0_INPUT, 'value'),
)
# @timer
def create_value(n_clicks, element_pk, value, date, response_pk, adm0):
    if None in [n_clicks, element_pk, value, response_pk]:
        raise PreventUpdate
    element = Variable.objects.get(pk=element_pk)
    if element.sd_type == "Constant":
        ResponseConstantValue(responseoption_id=response_pk, element_id=element_pk, value=value, admin0=adm0).save()
    elif element.sd_type == "Pulse Input":
        PulseValue(responseoption_id=response_pk, element_id=element_pk, value=value, startdate=date, admin0=adm0).save()
    # run_model(responseoption_pk=response_pk)
    return f"created {element.sd_type} value with value {value}"


@app.callback(
    Output("value-deleted-readout", "children"),
    Input({"type": "value-delete", "index": ALL}, "n_clicks"),
    State({"type": "value-delete", "index": ALL}, "id"),
)
def delete_value(n_clicks, ids):
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            constantvalue = ResponseConstantValue.objects.get(pk=id.get("index"))
            constantvalue.delete()
            # run_model(responseoption_pk=constantvalue.responseoption.pk)
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
            # run_model(responseoption_pk=pulsevalue.responseoption.pk)
            return f"{id} deleted, RERUN MODEL"
    raise PreventUpdate


@app.callback(
    Output("value-changed-readout", "children"),
    Input({"type": "value-change", "index": ALL}, "n_clicks"),
    State({"type": "value-change", "index": ALL}, "id"),
    State({"type": "value-change-input", "index": ALL}, "value"),
)
def change_value(n_clicks, ids, values):
    for n_click, id, value in zip(n_clicks, ids, values):
        if n_click is not None:
            if value is not None:
                value = ResponseConstantValue.objects.get(pk=id.get("index"))
                value.value = value
                value.save()
                # run_model(responseoption_pk=value.responseoption.pk)
                return f"{value} changed"
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
                # run_model(responseoption_pk=pulsevalue.responseoption.pk)
                return f"{pulsevalue} changed"
    raise PreventUpdate


@app.callback(
    Output("response-constants", "children"),
    Input("build-response-input", "value"),
    Input(ADMIN0_INPUT, "value"),
    Input("value-deleted-readout", "children"),
    Input("value-added-readout", "children"),
    Input("value-changed-readout", "children"),
    Input("pulse-deleted-readout", "children"),
    Input("pulse-changed-readout", "children"),
)
@timer
def build_response(response_pk, adm0, *_):
    # TODO: change to prefetch
    if response_pk is None:
        raise PreventUpdate
    response = ResponseOption.objects.get(pk=response_pk)
    table_header = [html.Thead(html.Tr([
        html.Th("Élément"), html.Th("Valeur"), html.Th("Unité"), html.Th("Date"), html.Th()
    ]))]
    table_rows = []
    for constantvalue in response.responseconstantvalues.filter(admin0=adm0):
        table_rows.append(html.Tr([
            html.Td(constantvalue.element.label),
            html.Td(dbc.InputGroup(size='sm', children=[
                dbc.Input(
                    value=constantvalue.value,
                    id={"type": "value-change-input", "index": constantvalue.pk}
                ),
                dbc.InputGroupAddon(dbc.Button(
                    "Changer",
                    id={"type": "value-change", "index": constantvalue.pk}),
                    addon_type="append"
                ),
            ])),
            html.Td(constantvalue.element.unit.replace('LCY', CURRENCY.get(adm0))),
            html.Td("N/A", style={"color": "gray"}),
            html.Td(dbc.Button(
                "Supprimer",
                id={"type": "value-delete", "index": constantvalue.pk},
                size="sm",
                color="danger",
                outline=True
            )),
        ]))

    for pulsevalue in response.pulsevalues.filter(admin0=adm0):
        table_rows.append(html.Tr([
            html.Td(pulsevalue.element.label),
            html.Td(dbc.InputGroup(size="sm", children=[
                dbc.Input(
                    value=pulsevalue.value,
                    id={"type": "pulse-change-input", "index": pulsevalue.pk}
                ),
                dbc.InputGroupAddon(dbc.Button(
                    "Changer",
                    id={"type": "pulse-change", "index": pulsevalue.pk}),
                    addon_type="append"
                ),
            ])),
            html.Td(pulsevalue.element.unit.replace('LCY', CURRENCY.get(adm0))),
            html.Td(pulsevalue.startdate),
            html.Td(dbc.Button(
                "Supprimer",
                id={"type": "pulse-delete", "index": pulsevalue.pk},
                size="sm",
                color="danger",
                outline=True
            )),
        ]))

    table_rows.append(html.Tr([
        html.Td(dbc.Select(
            id="value-element-input",
            placeholder="Ajouter un élément",
            options=[
                 {"label": element.label, "value": element.pk}
                 for element in Variable.objects.filter(sd_type__in=["Constant", "Pulse Input"])
            ]
        )),
        html.Td(dbc.Input(id="value-value-input")),
        html.Td(id="value-unit-input"),
        html.Td(dcc.DatePickerSingle(id='value-date-input')),
        html.Td(dbc.Button("Saisir", id="value-submit", size="sm"))
    ]))

    return dbc.Table(table_header + [html.Tbody(table_rows)])


@app.callback(
    Output("value-unit-input", "children"),
    Output('value-date-input', 'disabled'),
    Input("value-element-input", "value"),
    State(ADMIN0_INPUT, 'value'),
)
@timer
def newvalue_unit_and_date(element_pk, adm0):
    if element_pk is None:
        raise PreventUpdate
    variable = Variable.objects.get(pk=element_pk)
    unit = variable.unit
    disabled = True if variable.sd_type == 'Constant' else False
    return unit.replace('LCY', CURRENCY.get(adm0)), disabled

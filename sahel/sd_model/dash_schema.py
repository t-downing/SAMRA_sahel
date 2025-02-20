import re

import pandas as pd
from django_plotly_dash import DjangoDash
from dash import html, dcc, ctx
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_cytoscape as cyto
from sahel.models import Variable, SimulatedDataPoint, VariableConnection, ElementGroup, \
    MeasuredDataPoint, Source, ResponseOption, ResponseConstantValue, HouseholdConstantValue, Scenario, Element
import plotly.graph_objects as go
from sahel.sd_model.model_operations import run_model, timer
import inspect
from pprint import pprint
from datetime import date, datetime
from django.db.models import Max, Min
import time

admin1s = ["Gao", "Kidal", "Mopti", "Tombouctou", "Ménaka"]
initial_fig = go.Figure(layout=go.Layout(template="simple_white"))
initial_fig.update_xaxes(title_text="Date")
initial_startdate = date(2022, 1, 1)
initial_enddate = date(2023, 1, 1)

cyto.load_extra_layouts()

app = DjangoDash("sd_model", external_stylesheets=[dbc.themes.BOOTSTRAP])

stylesheet = [
    {"selector": "node",
     "style": {
         "content": "data(label)",
         "background-color": "data(color)",
         "width": 100,
         "height": 100,
         "border-width": 1,
         "text-valign": "center",
         "text-halign": "center",
         "text-wrap": "wrap",
         "text-max-width": 100,
         "background-opacity": 0.7,
     }},
    {"selector": "[sd_type = 'Stock']",
     "style": {
         "shape": "rectangle",
         "width": 150,
     }},
    {"selector": "[sd_type = 'Input']",
     "style": {
         "shape": "diamond",
     }},
    {"selector": "[sd_type = 'Household Constant']",
     "style": {
         "shape": "diamond",
     }},
    {"selector": "[sd_type = 'Constant']",
     "style": {
         "shape": "triangle",
         "text-valign": "bottom",
     }},
    {"selector": "[sd_type = 'Pulse Input']",
     "style": {
         "shape": "triangle",
         "text-valign": "bottom",
     }},
    {"selector": "edge",
     "style": {
         "target-arrow-color": "grey",
         "target-arrow-shape": "triangle",
         "line-color": "grey",
         "arrow-scale": 2,
         "width": 2,
         "curve-style": "unbundled-bezier",
         "control-point-distance": "50px",
         "z-index": 2,
     }},
    {"selector": "[edge_type = 'Flow']",
     "style": {
         "line-color": "lightgrey",
         "target-arrow-shape": "none",
         "mid-target-arrow-shape": "triangle",
         "mid-target-arrow-color": "grey",
         "width": 20,
         "arrow-scale": 0.4,
         "curve-style": "straight",
         "z-index": 1,
     }},
    {"selector": "[equation_stored = 'yes']",
     "style": {
         "color": "green",
     }},
    {"selector": "[has_equation = 'no']",
     "style": {
         "line-style": "dashed"
     }},
    {"selector": "[hierarchy = 'Group']",
     "style": {
         "text-valign": "top",
         "color": "lightgrey",
         "font-size": 40,
         "border-width": 3,
         "border-color": "lightgrey",
         "background-color": "white",
     }},
    {"selector": ":selected",
     "style": {
         "border-color": "blue",
         "border-width": 3,
     }},
]

ROWSTYLE = {"margin-bottom": "10px"}

app.layout = dbc.Container(style={"background-color": "#f8f9fc"}, fluid=True, children=[
    dbc.Row(children=[
        dbc.Col(
            [
                dbc.Card([
                    dbc.CardHeader("Contrôles", id="controls"),
                    dbc.CardBody([
                        dcc.Dropdown(id="admin1-input", options=admin1s, value=None, placeholder="Région",
                                     className="mb-2"),
                        dcc.Dropdown(id="admin2-input", options=admin1s, value=None, placeholder="Cercle",
                                     className="mb-2"),
                        # dcc.DatePickerRange(id="daterange-input", start_date=initial_startdate, end_date=initial_enddate, className="mb-2"),
                        dbc.Select(id="scenario-input", placeholder="Scénario", className="mb-2"),
                        dbc.Select(id="responseoption-input", placeholder="Réponse", className="mb-2"),
                        dbc.Button("Réexécuter modèle", n_clicks=0, id="run-model", disabled=True),
                    ])
                ], className="shadow mb-4 mt-4"),
                dbc.Card([
                    dbc.CardHeader("Ajouter un élément"),
                    dbc.CardBody([
                        dbc.Input(id="element-label-input", value="", style=ROWSTYLE, placeholder="Label"),
                        dbc.Select(id="element-type-input", value="", placeholder="Type", style=ROWSTYLE),
                        dbc.Select(id="element-unit-input", value="", placeholder="Unité", style=ROWSTYLE),
                        dbc.Button("Saisir", id="element-submit"),
                    ])
                ], className="shadow mb-4"),
            ],
            width=2
        ),
        dbc.Col(
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardHeader(
                    className="d-flex justify-content-between", style={"overflow": "hidden", "height": "50px"},
                    children=[
                        html.Div("Schéma"),
                        dbc.FormGroup([
                            dbc.Checklist(id="schema-group-switch",
                                          options=[{"label": "Montrer les détails", "value": 1}],
                                          value=[1], switch=True, inline=True),
                        ]),
                        # dbc.Switch(id="schema-group-switch", label="Montrer les détails", value=True),
                    ]
                ),
                dbc.CardBody([
                    cyto.Cytoscape(
                        id="cyto",
                        layout={"name": "preset"},
                        style={"background-color": "white", "height": "100%"},
                        stylesheet=stylesheet,
                        minZoom=0.2,
                        maxZoom=2.0,
                        boxSelectionEnabled=True,
                        autoRefreshLayout=True,
                    ),
                ], style={"padding": "0px"}),
                dbc.CardFooter(dbc.Row([
                    dbc.Col([dbc.Button("Sauvegarder mise en page", n_clicks=0, id="save-positions", size="sm",
                                        style={"marginRight": 10}),
                             dbc.Button("Download SVG", id="download", size="sm")]),
                    dbc.Col(dcc.Slider(id="map-date-input",
                                       min=initial_startdate.toordinal(),
                                       max=initial_enddate.toordinal(),
                                       value=initial_startdate.toordinal(),
                                       marks={mark_date.toordinal(): mark_date.strftime("%Y-%m-%d")
                                              for mark_date in pd.date_range(
                                               start=initial_startdate,
                                               end=initial_enddate,
                                               periods=4
                                           )}
                                       )),
                ]), style={"overflow": "hidden"}),
            ], style={"height": "900px"}, ),
            width=7
        ),
        dbc.Col(
            dbc.Card(className="shadow mb-4 mt-4", children=[
                dbc.CardHeader("Détail d'élément"),
                dbc.CardBody([
                    dbc.InputGroup([
                        dbc.InputGroupAddon("Label", addon_type="prepend"),
                        dbc.Input(id="element-detail-label-input"),
                        dbc.InputGroupAddon(dbc.Button("Changer", id="element-detail-label-submit"),
                                            addon_type="append"),
                    ], style=ROWSTYLE),
                    dbc.InputGroup([
                        dbc.InputGroupAddon("Type", addon_type="prepend"),
                        dbc.Select(id="element-detail-type-input"),
                        dbc.InputGroupAddon(dbc.Button("Changer", id="element-detail-type-submit"),
                                            addon_type="append"),
                    ], size="sm", style=ROWSTYLE),
                    dbc.InputGroup([
                        dbc.InputGroupAddon("Groupe", addon_type="prepend"),
                        dbc.Select(id="element-detail-group-input"),
                        dbc.InputGroupAddon(dbc.Button("Changer", id="element-detail-group-submit"),
                                            addon_type="append"),
                    ], size="sm", style=ROWSTYLE),
                    dcc.Graph(figure=initial_fig, id="element-detail-graph", style={"height": "300px"},
                              className="mb-2"),
                    html.Div(id="element-detail-conn-eq"),
                ])
            ], style={"height": "900px"}),
            width=3,
        )
    ]),
    html.H6("Debugging:", hidden=True),
    html.P(id="readout", hidden=True),
    html.P(id="model-ran-readout", hidden=True),
    html.P(id="readout3", hidden=True),
    html.P(id="connection-deleted-readout", hidden=True),
    html.P(id="element-created-readout", hidden=True),
    html.P(id="inflow-added", hidden=True),
    html.P(id="outflow-added", hidden=True),
    html.P(id="inflow-deleted-readout", hidden=True),
    html.P(id="outflow-deleted-readout", hidden=True),
    html.P(id="element-type-changed", hidden=True),
    html.P("initialized", id="equation-changed", hidden=True),
    html.P(id="elementgroup-changed", hidden=True),
    html.P(id="element-label-changed", hidden=True),
    html.P(id="householdconstantvalue-changed", hidden=True),
])


@app.callback(
    Output("scenario-input", "options"),
    Output("scenario-input", "value"),
    Output("responseoption-input", "options"),
    Output("responseoption-input", "value"),
    Output("element-type-input", "options"),
    Output("element-unit-input", "options"),
    Output("element-detail-type-input", "options"),
    Output("element-detail-group-input", "options"),
    Input("controls", "children"),
)
def populate_initial(_):
    scenario_options = [{"label": scenario.name, "value": scenario.pk}
                        for scenario in Scenario.objects.all()]
    scenario_value = 1
    response_options = [{"label": responseoption.name, "value": responseoption.pk}
                        for responseoption in ResponseOption.objects.all()]
    response_value = 1
    sdtype_options = [{"label": sd_type[1], "value": sd_type[0]} for sd_type in Variable.SD_TYPES]
    unit_options = [{"label": unit[1], "value": unit[0]} for unit in Variable.UNIT_OPTIONS]
    group_options = [{"label": group.label, "value": group.pk} for group in ElementGroup.objects.all()]
    return scenario_options, scenario_value, response_options, response_value, sdtype_options, unit_options, \
           sdtype_options, group_options


@app.callback(
    Output("cyto", "stylesheet"),
    Input("schema-group-switch", "value"),
)
def set_cyto_stylesheet(switch):
    print(switch)
    if switch == [1]:
        return stylesheet
    else:
        added_stylesheet = [
            {"selector": "node",
             "style": {
                 "visibility": "hidden",
             }},
            {"selector": "edge",
             "style": {
                 "visibility": "hidden",
             }},
            {"selector": "[hierarchy = 'Group']",
             "style": {
                 "visibility": "visible",
                 "background-color": "lightgray",
                 "border-color": "gray",
                 "color": "black",
                 "text-valign": "center",
                 "font-size": 80,
             }},
        ]
        return stylesheet + added_stylesheet


@app.callback(
    Output("map-date-input", "min"),
    Output("map-date-input", "value"),
    Output("map-date-input", "max"),
    Output("map-date-input", "marks"),
    Input("daterange-input", "start_date"),
    Input("daterange-input", "end_date"),
)
def update_slider(start_date, end_date):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    marks = {mark_date.toordinal(): mark_date.strftime("%Y-%m-%d")
             for mark_date in pd.date_range(
            start=start_date,
            end=end_date,
            periods=4
        )}
    return start_date.toordinal(), start_date.toordinal(), end_date.toordinal(), marks


@app.callback(
    Output("cyto", "generateImage"),
    Input("download", "n_clicks"),
    prevent_initial_call=True,
)
@timer
def download_svg(_):
    return {"type": "svg", "action": "download", "filename": "SAMRA_model_schema"}


@app.callback(
    Output("element-created-readout", "children"),
    Output("element-label-input", "value"),
    Output("element-type-input", "value"),
    Output("element-unit-input", "value"),
    Input("element-submit", "n_clicks"),
    State("element-label-input", "value"),
    State("element-type-input", "value"),
    State("element-unit-input", "value"),
)
@timer
def create_element(_, label, sd_type, unit):
    if label == "":
        return "need label", label, sd_type, unit
    if sd_type == "":
        return "need type", label, sd_type, unit
    if unit == "":
        return "need unit", label, sd_type, unit
    Variable(label=label, sd_type=sd_type, unit=unit).save()
    return f"created element '{label}'", "", "", ""


@app.callback(
    Output("connection-deleted-readout", "children"),
    Input({"type": "element-detail-conn-del", "index": ALL}, "n_clicks"),
    State({"type": "element-detail-conn-del", "index": ALL}, "id")
)
@timer
def delete_connection(n_clicks, ids):
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            pks = id.get("index").split("-to-")
            VariableConnection.objects.get(from_element__pk=pks[0], to_element__pk=pks[1]).delete()
            return f"{ids}"


@app.callback(
    Output("inflow-deleted-readout", "children"),
    Input({"type": "element-detail-inflow-del", "index": ALL}, "n_clicks"),
    State({"type": "element-detail-inflow-del", "index": ALL}, "id")
)
@timer
def delete_inflow(n_clicks, ids):
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            print(id)
            pks = id.get("index").split("-inflow-")
            flow = Variable.objects.get(pk=pks[1])
            flow.sd_sink = None
            flow.save()
            return f"deleted sink of {flow}"


@app.callback(
    Output("outflow-deleted-readout", "children"),
    Input({"type": "element-detail-outflow-del", "index": ALL}, "n_clicks"),
    State({"type": "element-detail-outflow-del", "index": ALL}, "id")
)
@timer
def delete_outflow(n_clicks, ids):
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            print(id)
            pks = id.get("index").split("-outflow-")
            flow = Variable.objects.get(pk=pks[1])
            flow.sd_source = None
            flow.save()
            return f"deleted sink of {flow}"


@app.callback(
    Output("element-detail-eq-text", "children"),
    Output("equation-changed", "children"),
    Input("element-detail-eq-submit", "n_clicks"),
    State("cyto", "tapNodeData"),
    State("element-detail-eq-input", "value"),
    prevent_initial_call=True,
)
@timer
def submit_equation(n_clicks, nodedata, value):
    if nodedata is None or value is None or n_clicks is None:
        raise PreventUpdate
    element = Variable.objects.get(pk=nodedata.get("id"))
    equation_text = value
    element.equation = value
    element_pks = re.findall(r"_E(.*?)_", equation_text)
    for element_pk in element_pks:
        upstream_element = Variable.objects.get(pk=element_pk)
        # if not upstream_element.equation_valid or upstream_element.equation is None:
        #     print(f"problem with {upstream_element}")
        equation_text = equation_text.replace(f"_E{element_pk}_", upstream_element.label)
    equation_text = f" = {equation_text}"
    element.save()
    return equation_text, f"equation changed for {element}; RERUN MODEL"


@app.callback(
    Output("householdconstantvalue-changed", "children"),
    Input("householdconstantvalue-submit", "n_clicks"),
    State("householdconstantvalue-input", "value"),
    State("cyto", "tapNodeData"),
)
def submit_householdconstantvalue(n_clicks, value, nodedata):
    if None in [n_clicks, value, nodedata]:
        raise PreventUpdate
    householdconstantvalue, _ = HouseholdConstantValue.objects.get_or_create(element_id=nodedata.get("id"))
    householdconstantvalue.value = value
    householdconstantvalue.save()
    return f"saved {householdconstantvalue} RERUN MODEL"


@app.callback(
    Output("readout3", "children"),
    Input("element-detail-conn-submit", "n_clicks"),
    State("cyto", "tapNodeData"),
    State("element-detail-conn-input", "value")
)
@timer
def submit_connection(n_clicks, nodedata, value):
    if value is None:
        return "nothing selected"
    element = Variable.objects.get(pk=nodedata.get("id"))
    upstream_element = Variable.objects.get(label=value)
    try:
        VariableConnection(from_variable=upstream_element, to_variable=element).save()
    except:
        return "could not add"
    return "added conenection"


@app.callback(
    Output("inflow-added", "children"),
    Input("element-detail-inflow-submit", "n_clicks"),
    State("cyto", "tapNodeData"),
    State("element-detail-inflow-input", "value")
)
def submit_inflow(_, nodedata, value):
    if value is None:
        return "no inflow selected"
    element = Variable.objects.get(pk=nodedata.get("id"))
    inflow = Variable.objects.get(pk=value)
    inflow.sd_sink = element
    inflow.save()
    return f"added {inflow} as inflow to {element}"


@app.callback(
    Output("outflow-added", "children"),
    Input("element-detail-outflow-submit", "n_clicks"),
    State("cyto", "tapNodeData"),
    State("element-detail-outflow-input", "value")
)
def submit_outflow(_, nodedata, value):
    if value is None:
        return "no outflow selected"
    element = Variable.objects.get(pk=nodedata.get("id"))
    outflow = Variable.objects.get(pk=value)
    outflow.sd_source = element
    outflow.save()
    return f"added {outflow} as inflow to {element}"


@app.callback(
    Output("model-ran-readout", "children"),
    Input("run-model", "n_clicks"),
    Input("equation-changed", "children"),
    Input("householdconstantvalue-changed", "children"),
    State("scenario-input", "value"),
    State("responseoption-input", "value"),
    prevent_initial_call=True,
)
@timer
def run_model_from_cyto(n_clicks, eq_readout, cv_readout, scenario_pk, response_pk):
    if "RERUN MODEL" in eq_readout or "RERUN MODEL" in cv_readout:
        run_model(scenario_pk=scenario_pk, responseoption_pk=response_pk)
        return f"ran model with scenario_pk {scenario_pk} and response_pk {response_pk}"
    return "didn't run model"


@app.callback(
    Output("element-detail-label-input", "value"),
    Output("element-detail-type-input", "value"),
    # Output("element-detail-group-input", "value"),
    Input("cyto", "tapNodeData"),
    State("cyto", "tapNode"),
)
def element_detail_title(nodedata, layout):
    if nodedata is None:
        raise PreventUpdate
    if nodedata.get("hierarchy") == "Group":
        return None, None, None
    element = Variable.objects.get(pk=nodedata.get("id"))
    # group = None if element.element_group is None else element.element_group.pk
    return element.label, element.sd_type # group


@app.callback(
    Output("element-label-changed", "children"),
    Input("element-detail-label-submit", "n_clicks"),
    State("element-detail-label-input", "value"),
    State("cyto", "tapNodeData"),
)
def element_label_submit(_, label, nodedata):
    if None in [label, nodedata]:
        raise PreventUpdate
    element = Variable.objects.get(pk=nodedata.get("id"))
    element.label = label
    element.save()
    return f"{element} label updated"


@app.callback(
    Output("elementgroup-changed", "children"),
    Input("element-detail-group-submit", "n_clicks"),
    State("element-detail-group-input", "value"),
    State("cyto", "tapNodeData"),
)
def elementgroup_submit(_, group_pk, nodedata):
    if None in [group_pk, nodedata]:
        raise PreventUpdate
    element = Variable.objects.get(pk=nodedata.get("id"))
    element.element_group_id = group_pk
    element.save()
    return f"{element} is now part of {element.element_group}"


@app.callback(
    Output("element-type-changed", "children"),
    Input("element-detail-type-submit", "n_clicks"),
    State("element-detail-type-input", "value"),
    State("cyto", "tapNodeData")
)
def submit_type(_, sd_type, nodedata):
    if None in [sd_type, nodedata]:
        raise PreventUpdate
    element = Variable.objects.get(pk=nodedata.get("id"))
    element.sd_type = sd_type
    element.save()
    return f"changed {element} to {sd_type}"


@app.callback(
    Output("element-detail-graph", "figure"),
    Input("cyto", "tapNodeData"),
    Input("admin1-input", "value"),
    Input("scenario-input", "value"),
    Input("responseoption-input", "value"),
    Input("model-ran-readout", "children"),
)
@timer
def element_detail_graph(nodedata, admin1, scenario_pk, responseoption_pk, *_):
    fig = go.Figure(layout=go.Layout(template="simple_white", margin=go.layout.Margin(l=0, r=0, b=0, t=0)))
    fig.update_xaxes(title_text="Date")
    if nodedata is None or nodedata.get("hierarchy") == "Group":
        return fig

    element = Variable.objects.get(pk=nodedata.get("id"))

    df = pd.DataFrame(SimulatedDataPoint.objects
                      .filter(element=element, scenario_id=scenario_pk, responseoption_id=responseoption_pk)
                      .values("date", "value"))

    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["value"],
            name="Simulé",
        ))

    if admin1 is None:
        df = pd.DataFrame(MeasuredDataPoint.objects.filter(element=element).values())
    else:
        df = pd.DataFrame(MeasuredDataPoint.objects.filter(element=element, admin1=admin1).values())

    if not df.empty:
        source_ids = df["source_id"].drop_duplicates()
        for source_id in source_ids:
            try:
                source = Source.objects.get(pk=source_id)
            except Source.DoesNotExist:
                print(f"no source for datapoint in {element}")
                continue
            dff = df[df["source_id"] == source_id].groupby("date").mean().reset_index()
            fig.add_trace(go.Scatter(
                x=dff["date"],
                y=dff["value"],
                name=source.title,
            ))
    unit_append = " / mois" if element.sd_type == "Pulse Input" else ""
    fig.update_layout(
        legend=dict(yanchor="bottom", x=0, y=1),
        showlegend=True,
        yaxis=dict(title=element.unit + unit_append),
    )
    return fig


@app.callback(
    Output("element-detail-conn-eq", "children"),
    Input("cyto", "tapNodeData"),
    Input("readout3", "children"),
    Input("connection-deleted-readout", "children"),
    State("responseoption-input", "value")
)
def element_detail_conn_eq(nodedata, _, _1, response_pk):
    if nodedata is None or nodedata.get("hierarchy") == "Group":
        return None

    variable = Variable.objects.get(pk=nodedata.get("id"))
    if variable.sd_type in ["Flow", "Variable"]:
        upstream_variables = Variable.objects.filter(downstream_connections__to_variable=variable)
        upstream_list = dbc.ListGroup(
            [
                dbc.ListGroupItem(className="p-1 justify-content-between", children=
                html.Div(className="d-flex justify-content-between", children=
                [
                    html.P(style={"font-size": "small"},
                           children=f"{upstream_variable.label} _E{upstream_variable.pk}_"),
                    dbc.Button("X",
                               id={"type": "element-detail-conn-del",
                                   "index": f"{upstream_variable.pk}-to-{variable.pk}"},
                               size="sm",
                               color="danger",
                               className="p-1",
                               outline=True)
                ],

                         )
                                  )
                for upstream_variable in upstream_variables
            ],
            flush=True,
            style={"height": "150px", "overflow-y": "scroll"}
        )

        dropdown_options = Variable.objects.exclude(downstream_connections__to_variable=variable).exclude(
            pk=variable.pk)
        dropdown_list = [
            {"label": possible_variable.label, "value": possible_variable.label}
            for possible_variable in dropdown_options
        ]

        upstream_card = dbc.Card(className="mb-2", children=[
            dbc.CardHeader("Influencé par", className="p-1", style={"font-size": "small"}),
            dbc.CardBody(
                [
                    upstream_list,
                    dbc.InputGroup(children=[
                        dbc.Select(options=dropdown_list, id="element-detail-conn-input",
                                   placeholder="Ajouter une influence", bs_size="sm"),
                        dbc.InputGroupAddon(dbc.Button("Saisir", id="element-detail-conn-submit", size="sm"),
                                            addon_type="append")
                    ]),
                ],
                style={"padding": "0px"},
            )
        ])

        equation_text = variable.equation
        if equation_text is not None:
            print(f"equation is {equation_text}")
            for key_element in Variable.objects.all():
                equation_text = equation_text.replace(f"_E{key_element.pk}_", key_element.label)
            print(f"after swap equation is {equation_text}")
            equation_text = f" = {equation_text}"

        equation_card = dbc.Card([
            dbc.CardHeader("Équation", className="p-1", style={"font-size": "small"}),
            dbc.CardBody(className="p-2", children=
            [
                html.P(equation_text, id="element-detail-eq-text",
                       style={"font-size": "small", "height": "50px", "overflow-y": "scroll"}),
                dbc.InputGroup([
                    dbc.Input(value=variable.equation, id="element-detail-eq-input", bs_size="sm"),
                    dbc.InputGroupAddon(dbc.Button("Saisir", id="element-detail-eq-submit", size="sm"),
                                        addon_type="append"),
                ]),

            ]
                         )
        ])

        conn_eq_div = html.Div([
            upstream_card,
            equation_card,
        ])
    elif variable.sd_type == "Stock":
        inflows_card = dbc.Card([
            dbc.CardHeader(className="p-1", style={"font-size": "small"}, children="Flux intrants"),
            dbc.CardBody(style={"padding": "0px"}, children=[
                dbc.ListGroup(
                    [
                        dbc.ListGroupItem(className="p-1 d-flex justify-content-between", style={"font-size": "small"},
                                          children=[
                                              inflow.label,
                                              dbc.Button("X",
                                                         id={"type": "element-detail-inflow-del",
                                                             "index": f"{variable.pk}-inflow-{inflow.pk}"},
                                                         size="sm", color="danger", className="p-1", outline=True)
                                          ])
                        for inflow in variable.inflows.all()
                    ],
                    flush=True,
                    style={"height": "100px", "overflow-y": "scroll"}
                ),
                dbc.InputGroup([
                    dbc.Select(id="element-detail-inflow-input", bs_size="sm", placeholder="Ajouter un flux entrant",
                               options=[
                                   {"label": potential_inflow.label, "value": potential_inflow.pk}
                                   for potential_inflow in Variable.objects.filter(sd_type="Flow")
                               .exclude(sd_sink__isnull=False).exclude(sd_source=variable)
                               ]),
                    dbc.Button("Saisir", id="element-detail-inflow-submit", size="sm")
                ])
            ])
        ], style=ROWSTYLE)

        outflows_card = dbc.Card([
            dbc.CardHeader(className="p-1", style={"font-size": "small"}, children="Flux sortants"),
            dbc.CardBody(style={"padding": "0px"}, children=[
                dbc.ListGroup(
                    [
                        dbc.ListGroupItem(className="p-1 d-flex justify-content-between", style={"font-size": "small"},
                                          children=[
                                              outflow.label,
                                              dbc.Button("X",
                                                         id={"type": "element-detail-outflow-del",
                                                             "index": f"{variable.pk}-outflow-{outflow.pk}"},
                                                         size="sm", color="danger", className="p-1", outline=True)
                                          ])
                        for outflow in variable.outflows.all()
                    ],
                    flush=True,
                    style={"height": "100px", "overflow-y": "scroll"}
                ),
                dbc.InputGroup([
                    dbc.Select(id="element-detail-outflow-input", bs_size="sm", placeholder="Ajouter un flux sortant",
                               options=[
                                   {"label": potential_outflow.label, "value": potential_outflow.pk}
                                   for potential_outflow in
                                   Variable.objects.filter(sd_type="Flow").exclude(sd_sink=variable).exclude(
                                       sd_source=variable)
                               ]),
                    dbc.Button("Saisir", id="element-detail-outflow-submit", size="sm")
                ])
            ])
        ], style=ROWSTYLE)

        conn_eq_div = html.Div([inflows_card, outflows_card])
    elif variable.sd_type == "Household Constant":
        try:
            value = variable.householdconstantvalues.get().value
        except HouseholdConstantValue.DoesNotExist:
            value = None
        conn_eq_div = dbc.InputGroup([
            dbc.InputGroupText("Value"),
            dbc.Input(id="householdconstantvalue-input", value=value),
            dbc.Button("Saisir", id="householdconstantvalue-submit")
        ])
    else:
        conn_eq_div = None

    return conn_eq_div


@app.callback(
    Output("readout", "children"),
    Input("save-positions", "n_clicks"),
    State("cyto", "elements"),
    State("cyto", "layout")
)
@timer
def save_element_positions(n_clicks, cyto_elements, layout):
    if n_clicks == 0:
        return "not saved yet"
    elements = []
    for cyto_element in cyto_elements:
        # print(f"found for {cyto_element}")
        if "position" in cyto_element:
            element = Variable.objects.get(pk=cyto_element.get("data").get("id"))
            element.x_pos, element.y_pos = cyto_element.get("position").get("x"), cyto_element.get("position").get("y")
            # print(f"saving position for {element}")
            elements.append(element)
    Variable.objects.bulk_update(elements, ["x_pos", "y_pos"])
    return f"saved {n_clicks} times"


@app.callback(
    Output("cyto", "elements"),
    Input("map-date-input", "value"),
    Input("element-created-readout", "children"),
    Input("element-type-changed", "children"),
)
@timer
def redraw_model(date_ord, *_):
    start = time.time()
    variables = Variable.objects.exclude(label__contains="HELLO").values()
    nodes = []
    for variable in variables:
        color = "white"

        nodes.append(
            {"data": {"id": variable.get("id"),
                      "label": variable.get("label"),
                      "sd_type": variable.get("sd_type"),
                      "equation_stored": "yes" if variable.get("equation") else "no",
                      "parent": None,
                      "color": color},
             "position": {"x": variable.get("x_pos"), "y": variable.get("y_pos")}}
        )
    print(f"elements took {time.time() - start}")
    start = time.time()

    # element_groups = ElementGroup.objects.all().values()
    # group_nodes = [
    #     {"data": {"id": f"group_{element_group.get('id')}",
    #               "label": element_group.get("label"),
    #               "hierarchy": "Group"},
    #      "grabbable": False,
    #      "selectable": False,
    #      "pannable": True}
    #     for element_group in element_groups
    # ]
    # print(f"groups took {time.time() - start}")
    # start = time.time()

    connections = VariableConnection.objects.all().select_related("to_variable")
    edges = []
    eq_time = 0
    append_time = 0
    eq_read_time = 0
    for connection in connections:
        eq_start = time.time()
        has_equation = "no"
        if connection.to_variable is not None:
            if connection.to_variable.equation is not None:
                eq_read_start = time.time()
                has_equation = "yes" if f"_E{connection.from_variable_id}_" in connection.to_variable.equation else "no"
                eq_read_time += time.time() - eq_read_start

        eq_time += time.time() - eq_start
        append_start = time.time()
        edges.append({"data": {"source": connection.from_variable_id,
                               "target": connection.to_variable_id,
                               "has_equation": has_equation}})
        append_time += time.time() - append_start
    print(f"eq took {eq_time}, eq_read took {eq_read_time}, append took {append_time}")
    print(f"connections took {time.time() - start}")
    start = time.time()

    flow_edges = []
    stocks = Variable.objects.filter(sd_type="Stock").prefetch_related("inflows", "outflows")
    for stock in stocks:
        for inflow in stock.inflows.all():
            has_equation = "no" if inflow.equation is None else "yes"
            flow_edges.append(
                {"data": {"source": inflow.pk,
                          "target": stock.pk,
                          "has_equation": has_equation,
                          "edge_type": "Flow"}}
            )
        for outflow in stock.outflows.all():
            has_equation = "no" if outflow.equation is None else "yes"
            flow_edges.append(
                {"data": {"source": stock.pk,
                          "target": outflow.pk,
                          "has_equation": has_equation,
                          "edge_type": "Flow"}}
            )
    print(f"stocks took {time.time() - start}")
    start = time.time()
    return nodes + edges + flow_edges

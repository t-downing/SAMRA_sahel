import re

import pandas as pd
from django_plotly_dash import DjangoDash
from dash import html, dcc, ctx
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_cytoscape as cyto
from ...models import Element, SimulatedDataPoint, Connection, ElementGroup, \
    MeasuredDataPoint, Source, ResponseOption, ConstantValue, HouseholdConstantValue
import plotly.graph_objects as go
from ..model_operations import run_model, timer
import inspect
from pprint import pprint
from datetime import date, datetime
from django.db.models import Max, Min

admin1s = ["Gao", "Kidal", "Mopti", "Tombouctou", "Ménaka"]
initial_fig = go.Figure(layout=go.Layout(template="simple_white"))
initial_fig.update_xaxes(title_text="Date")
initial_startdate = date(2022, 1, 1)
initial_enddate = date(2023, 1, 1)
initial_response = 1

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

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(
            [
                dbc.Card([
                    dbc.CardHeader("Contrôles"),
                    dbc.CardBody([
                        dcc.Dropdown(id="admin1-input", options=admin1s, value=None, placeholder="Région", style=ROWSTYLE),
                        dcc.Dropdown(id="admin2-input", options=admin1s, value=None, placeholder="Cercle", style=ROWSTYLE),
                        dcc.DatePickerRange(id="daterange-input", start_date=initial_startdate, end_date=initial_enddate, style=ROWSTYLE),
                        dbc.Select(id="responseoption-input", placeholder="Réponse", value=initial_response,
                                   options=[{"label": responseoption.name, "value": responseoption.pk}
                                            for responseoption in ResponseOption.objects.all()]),
                        dbc.Button("Réexécuter modèle", n_clicks=0, id="run-model"),
                    ])
                ], style=ROWSTYLE),
                dbc.Card([
                    dbc.CardHeader("Ajouter un élément"),
                    dbc.CardBody([
                        dbc.Input(id="element-label-input", value="", style=ROWSTYLE, placeholder="Label"),
                        dbc.Select(id="element-type-input", value="", placeholder="Type",
                                     options=[{"label": sd_type[1], "type": sd_type[0]} for sd_type in Element.SD_TYPES], style=ROWSTYLE),
                        dbc.Select(id="element-unit-input", value="", placeholder="Unité",
                                   options=[{"label": unit[1], "value": unit[1]} for unit in Element.UNIT_OPTIONS],
                                   style=ROWSTYLE),
                        dbc.Button("Saisir", id="element-submit"),
                    ])
                ]),
            ],
            width=2
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader([
                    html.Div("Schéma"),
                    dbc.Switch(id="schema-group-switch", label="Montrer les détails", value=True),
                ], className="d-flex justify-content-between"),
                dbc.CardBody([
                    cyto.Cytoscape(
                        id="cyto",
                        layout={"name": "preset"},
                        style={"background-color": "white", "height": "100%"},
                        stylesheet=stylesheet,
                        minZoom=0.2,
                        maxZoom=2.0,
                        # autoRefreshLayout=True
                    ),
                ], style={"padding": "0px"}),
                dbc.CardFooter(dbc.Row([
                    dbc.Col([dbc.Button("Sauvegarder positions d'éléments", n_clicks=0, id="save-positions", size="sm",
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
            ], style={"height": "900px"}),
            width=7
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Détail d'élément"),
                dbc.CardBody([
                    dbc.InputGroup([
                        dbc.InputGroupText("Label"),
                        dbc.Input(id="element-detail-label-input"),
                        dbc.Button("Changer", id="element-detail-label-submit"),
                    ], style=ROWSTYLE),
                    dbc.InputGroup([
                        dbc.InputGroupText("Type"),
                        dbc.Select(id="element-detail-type-input",
                                   options=[{"label": sd_type[1], "value": sd_type[0]} for sd_type in Element.SD_TYPES]),
                        dbc.Button("Changer", id="element-detail-type-submit")
                    ], size="sm", style=ROWSTYLE),
                    dbc.InputGroup([
                        dbc.InputGroupText("Groupe"),
                        dbc.Select(id="element-detail-group-input",
                                   options=[{"label": group.label, "value": group.pk} for group in ElementGroup.objects.all()]),
                        dbc.Button("Changer", id="element-detail-group-submit")
                    ], size="sm", style=ROWSTYLE),
                    dcc.Graph(figure=initial_fig, id="element-detail-graph", style={"height": "300px"}),
                    html.Div(id="element-detail-conn-eq"),
                ])
            ], style={"height": "900px"}),
            width=3,
        )
    ]),
    html.H6("Debugging:"),
    html.P(id="readout"),
    html.P(id="model-ran-readout"),
    html.P(id="readout3"),
    html.P(id="connection-deleted-readout"),
    html.P(id="element-created-readout"),
    html.P(id="inflow-added"),
    html.P(id="outflow-added"),
    html.P(id="inflow-deleted-readout"),
    html.P(id="outflow-deleted-readout"),
    html.P(id="element-type-changed"),
    html.P("initialized", id="equation-changed"),
    html.P(id="elementgroup-changed"),
    html.P(id="element-label-changed"),
    html.P(id="householdconstantvalue-changed"),
], fluid=True)


@app.callback(
    Output("cyto", "stylesheet"),
    Input("schema-group-switch", "value"),
)
def set_cyto_stylesheet(switch):
    print(switch)
    if switch:
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
    if unit =="":
        return "need unit", label, sd_type, unit
    Element(label=label, sd_type=sd_type, unit=unit).save()
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
            Connection.objects.get(from_element__pk=pks[0], to_element__pk=pks[1]).delete()
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
            flow = Element.objects.get(pk=pks[1])
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
            flow = Element.objects.get(pk=pks[1])
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
    element = Element.objects.get(pk=nodedata.get("id"))
    equation_text = value
    element.equation = value
    element_pks = re.findall(r"_E(.*?)_", equation_text)
    for element_pk in element_pks:
        upstream_element = Element.objects.get(pk=element_pk)
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
    element = Element.objects.get(pk=nodedata.get("id"))
    upstream_element = Element.objects.get(label=value)
    try:
        Connection(from_element=upstream_element, to_element=element).save()
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
    element = Element.objects.get(pk=nodedata.get("id"))
    inflow = Element.objects.get(pk=value)
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
    element = Element.objects.get(pk=nodedata.get("id"))
    outflow = Element.objects.get(pk=value)
    outflow.sd_source = element
    outflow.save()
    return f"added {outflow} as inflow to {element}"


@app.callback(
    Output("model-ran-readout", "children"),
    Input("run-model", "n_clicks"),
    Input("equation-changed", "children"),
    Input("householdconstantvalue-changed", "children"),
    State("responseoption-input", "value"),
    prevent_initial_call=True,
)
@timer
def run_model_from_cyto(n_clicks, eq_readout, cv_readout, response_pk):
    if "RERUN MODEL" in eq_readout or "RERUN MODEL" in cv_readout:
        run_model(responseoption_pk=response_pk)
        return f"ran model with response_pk {response_pk}"
    return "didn't run model"


@app.callback(
    Output("element-detail-label-input", "value"),
    Output("element-detail-type-input", "value"),
    Output("element-detail-group-input", "value"),
    Input("cyto", "tapNodeData"),
    State("cyto", "tapNode"),
)
def element_detail_title(nodedata, layout):
    if nodedata is None:
        raise PreventUpdate
    if nodedata.get("hierarchy") == "Group":
        return None, None, None
    element = Element.objects.get(pk=nodedata.get("id"))
    group = None if element.element_group is None else element.element_group.pk
    return element.label, element.sd_type, group


@app.callback(
    Output("element-label-changed", "children"),
    Input("element-detail-label-submit", "n_clicks"),
    State("element-detail-label-input", "value"),
    State("cyto", "tapNodeData"),
)
def element_label_submit(_, label, nodedata):
    if None in [label, nodedata]:
        raise PreventUpdate
    element = Element.objects.get(pk=nodedata.get("id"))
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
    element = Element.objects.get(pk=nodedata.get("id"))
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
    element = Element.objects.get(pk=nodedata.get("id"))
    element.sd_type = sd_type
    element.save()
    return f"changed {element} to {sd_type}"


@app.callback(
    Output("element-detail-graph", "figure"),
    Input("cyto", "tapNodeData"),
    Input("admin1-input", "value"),
    Input("responseoption-input", "value"),
    Input("model-ran-readout", "children"),
)
@timer
def element_detail_graph(nodedata, admin1, responseoption_pk, *_):
    fig = go.Figure(layout=go.Layout(template="simple_white", margin=go.layout.Margin(l=0, r=0, b=0, t=0)))
    fig.update_xaxes(title_text="Date")
    if nodedata is None or nodedata.get("hierarchy") == "Group":
        return fig

    element = Element.objects.get(pk=nodedata.get("id"))

    df = pd.DataFrame(SimulatedDataPoint.objects.filter(element=element, responseoption_id=responseoption_pk).values("date", "value"))
    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["value"],
            name="Simulé",
        ))

    if admin1 is None:
        df = pd.DataFrame(list(MeasuredDataPoint.objects.filter(element=element).values()))
    else:
        df = pd.DataFrame(list(MeasuredDataPoint.objects.filter(element=element, admin1=admin1).values()))
    if not df.empty:
        source_ids = df["source_id"].drop_duplicates()
        for source_id in source_ids:
            source = Source.objects.get(pk=source_id)
            print(source)
            dff = df[df["source_id"] == source_id].groupby("date").mean().reset_index()
            fig.add_trace(go.Scatter(
                x=dff["date"],
                y=dff["value"],
                name=source.title,
            ))
    fig.update_layout(
        legend=dict(yanchor="bottom", x=0, y=1),
        showlegend=True,
        yaxis=dict(title=element.unit),
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

    element = Element.objects.get(pk=nodedata.get("id"))
    if element.sd_type in ["Flow", "Variable"]:
        upstream_elements = Element.objects.filter(downstream_connections__to_element=element)
        upstream_list = dbc.ListGroup(
            [
                dbc.ListGroupItem(
                    html.Div(
                        [
                            html.P(f"{upstream_element.label} _E{upstream_element.pk}_"),
                            dbc.Button("Supprimer",
                                       id={"type": "element-detail-conn-del",
                                           "index": f"{upstream_element.pk}-to-{element.pk}"},
                                       size="sm",
                                       color="danger",
                                       outline=True)
                        ],
                        className="d-flex justify-content-between"
                    )
                )
                for upstream_element in upstream_elements
            ],
            flush=True,
            style={"height": "150px", "overflow-y": "scroll"}
        )

        dropdown_options = Element.objects.exclude(downstream_connections__to_element=element).exclude(pk=element.pk)
        dropdown_list = [
            {"label": possible_element.label, "value": possible_element.label}
            for possible_element in dropdown_options
        ]

        upstream_card = dbc.Card([
            dbc.CardHeader("Influencé par"),
            dbc.CardBody(
                [
                    upstream_list,
                    dbc.InputGroup([
                        dbc.Select(options=dropdown_list, id="element-detail-conn-input", placeholder="Ajouter une influence"),
                        dbc.Button("Saisir", id="element-detail-conn-submit")
                    ]),
                ],
                style={"padding": "0px"},
            )
        ], style=ROWSTYLE)

        equation_text = element.equation
        if equation_text is not None:
            print(f"equation is {equation_text}")
            for key_element in Element.objects.all():
                equation_text = equation_text.replace(f"_E{key_element.pk}_", key_element.label)
            print(f"after swap equation is {equation_text}")
            equation_text = f" = {equation_text}"

        equation_card = dbc.Card([
            dbc.CardHeader("Équation"),
            dbc.CardBody(
                [
                    html.P(equation_text, id="element-detail-eq-text"),
                    dbc.InputGroup([
                        dbc.Input(value=element.equation, id="element-detail-eq-input"),
                        dbc.Button("Saisir", id="element-detail-eq-submit")
                    ]),

                ]
            )
        ])

        conn_eq_div = html.Div([
            upstream_card,
            equation_card,
        ])
    elif element.sd_type == "Stock":
        inflows_card = dbc.Card([
            dbc.CardHeader("Flux intrants"),
            dbc.CardBody([
                dbc.ListGroup(
                    [
                        dbc.ListGroupItem([
                            inflow.label,
                            dbc.Button("Supprimer",
                                       id={"type": "element-detail-inflow-del",
                                           "index": f"{element.pk}-inflow-{inflow.pk}"},
                                       size="sm", color="danger", outline=True)
                        ])
                        for inflow in element.inflows.all()
                    ],
                    flush=True,
                    style={"height": "150px", "overflow-y": "scroll"}
                ),
                dbc.InputGroup([
                    dbc.Select(id="element-detail-inflow-input", placeholder="Ajouter un flux entrant",
                               options=[
                                    {"label": potential_inflow.label, "value": potential_inflow.pk}
                                    for potential_inflow in Element.objects.filter(sd_type="Flow")
                                        .exclude(sd_sink__isnull=False).exclude(sd_source=element)
                                ]),
                    dbc.Button("Saisir", id="element-detail-inflow-submit")
                ])
            ], style={"padding": "0px"})
        ], style=ROWSTYLE)

        outflows_card = dbc.Card([
            dbc.CardHeader("Flux sortants"),
            dbc.CardBody([
                dbc.ListGroup(
                    [
                        dbc.ListGroupItem([
                            outflow.label,
                            dbc.Button("Supprimer",
                                       id={"type": "element-detail-outflow-del",
                                           "index": f"{element.pk}-outflow-{outflow.pk}"},
                                       size="sm", color="danger", outline=True)
                        ])
                        for outflow in element.outflows.all()
                    ],
                    flush=True,
                    style={"height": "200px", "overflow-y": "scroll"}
                ),
                dbc.InputGroup([
                    dbc.Select(id="element-detail-outflow-input", placeholder="Ajouter un flux sortant",
                               options=[
                                   {"label": potential_outflow.label, "value": potential_outflow.pk}
                                   for potential_outflow in Element.objects.filter(sd_type="Flow").exclude(sd_sink=element).exclude(sd_source=element)
                               ]),
                    dbc.Button("Saisir", id="element-detail-outflow-submit")
                ])
            ], style={"padding": "0px"})
        ], style=ROWSTYLE)

        conn_eq_div = html.Div([inflows_card, outflows_card])
    elif element.sd_type == "Household Constant":
        try:
            value = element.householdconstantvalues.get().value
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
        if "position" in cyto_element:
            element = Element.objects.get(pk=cyto_element.get("data").get("id"))
            element.x_pos, element.y_pos = cyto_element.get("position").get("x"), cyto_element.get("position").get("y")
            elements.append(element)
    Element.objects.bulk_update(elements, ["x_pos", "y_pos"])
    return "saved"


@app.callback(
    Output("cyto", "elements"),
    Input("map-date-input", "value"),
    Input("element-created-readout", "children"),
    Input("element-type-changed", "children"),
)
@timer
def redraw_model(date_ord, *_):
    elements = Element.objects.all()
    nodes =[]
    for element in elements:
        dateinput = date.fromordinal(int(date_ord))
        datapoint = element.measureddatapoints.filter(element=element, date__lte=dateinput).order_by("-date").first()
        if datapoint is not None:
            max_value = element.measureddatapoints.aggregate(Max("value")).get("value__max")
            min_value = element.measureddatapoints.aggregate(Min("value")).get("value__min")
            value_norm = (datapoint.value - min_value) / (max_value - min_value)
            if value_norm < 1/3:
                color = "lightcoral"
            elif value_norm < 2/3:
                color = "khaki"
            else:
                color = "lightgreen"
            for node in nodes:
                if node.get("data").get("id") == element.pk:
                    node["data"]["color"] = color
        else:
            color = "white"

        nodes.append(
            {"data": {"id": element.pk,
                      "label": element.label,
                      "sd_type": element.sd_type,
                      "sim_input_var": element.sim_input_var,
                      "equation_stored": "yes" if element.equation else "no",
                      "parent": None if element.element_group is None else f"group_{element.element_group.pk}",
                      "color": color},
             "position": {"x": element.x_pos, "y": element.y_pos}}
        )

    element_groups = ElementGroup.objects.all()
    group_nodes = [{"data": {"id": f"group_{element_group.pk}",
                             "label": element_group.label,
                             "hierarchy": "Group"},
                    "grabbable": False,
                    "selectable": False,
                    "pannable": True}
        for element_group in element_groups
    ]

    connections = Connection.objects.all()
    edges=[]
    for connection in connections:
        if connection.to_element.equation is not None:
            has_equation = "yes" if f"_E{connection.from_element.pk}_" in connection.to_element.equation else "no"
        else:
            has_equation = "no"
        edges.append({"data": {"source": connection.from_element.pk,
                                "target": connection.to_element.pk,
                                "has_equation": has_equation}})

    flow_edges = []
    stocks = Element.objects.filter(sd_type="Stock")
    for stock in stocks:
        for inflow in stock.inflows.all():
            flow_edges.append(
                {"data": {"source": inflow.pk,
                          "target": stock.pk,
                          "edge_type": "Flow"}}
            )
        for outflow in stock.outflows.all():
            flow_edges.append(
                {"data": {"source": stock.pk,
                          "target": outflow.pk,
                          "edge_type": "Flow"}}
            )
    # print([pan, zoom])
    return nodes + group_nodes + edges + flow_edges
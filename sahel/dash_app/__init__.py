import pandas as pd
from django_plotly_dash import DjangoDash
from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash_cytoscape as cyto
from ..models import Element, SimulatedDataPoint, Connection, SYSTEM_DYNAMICS_TYPES
import plotly.graph_objects as go
from .sd_model import run_model

app = DjangoDash("sd_model", external_stylesheets=[dbc.themes.BOOTSTRAP])

stylesheet = [
    {"selector": "node",
     "style": {
         "content": "data(label)",
         "background-color": "white",
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
    {"selector": "edge",
     "style": {
         "target-arrow-color": "grey",
         "target-arrow-shape": "triangle",
         "line-color": "grey",
         "arrow-scale": 2,
         "width": 2,
         "curve-style": "unbundled-bezier",
         "control-point-distance": "50px",
     }},
    {"selector": "[edge_type = 'Flow']",
     "style": {
         "line-color": "lightgrey",
         "target-arrow-shape": "none",
         "mid-target-arrow-shape": "triangle-backcurve",
         "mid-target-arrow-color": "black",
         "mid-target-arrow-fill": "hollow",
         "width": 20,
         "arrow-scale": 1.2,
         "curve-style": "straight",
     }},
    {"selector": "[equation_stored = 'yes']",
     "style": {
         "color": "green",
     }}
]

app.layout = html.Div([
    html.Div([
        cyto.Cytoscape(
            id="cyto",
            layout={"name": "preset"},
            style={"width": "59%", "height": "600px", "background-color": "white", "border": "1px lightgrey solid",
                   "display": "inline-block"},
            stylesheet=stylesheet,
            autoRefreshLayout=True,
        ),
        html.Div(
            [
                dcc.Graph(id="element-graph", style={"height": "400px"}),
                html.Div([
                    html.Div(["Influencé par:"]),
                    html.Div(id="element-connections"),
                    html.Div([dcc.Dropdown(id="element-connection-input", placeholder="Ajouter une influence"),
                              dbc.Button("Saisir", n_clicks=0, id="element-connection-submit")]),
                    html.Div(id="element-equation"),
                    dcc.Input(id="element-equation-input", type="text", placeholder="Saisir une nouvelle équation"),
                    dbc.Button("Saisir et réexécuter le modèle", id="element-equation-submit"),
                ], id="element-readout", style={"height": "200px"})
            ],
            style={"height": "600px", "width": "40%", "display": "inline-block", "vertical-align": "top"},
        )

    ]),
    html.Div([
        dbc.Button("Sauvegarder positions d'éléments", n_clicks=0, id="save-positions"),
        dbc.Button("Réexécuter modèle", n_clicks=0, id="run-model"),
        html.Div([
            dcc.Input(id="element-label-input", value=""),
            dcc.Dropdown(id="element-type-input", value="", options=[sd_type[1] for sd_type in SYSTEM_DYNAMICS_TYPES]),
            dbc.Button("Saisir", id="element-submit")
        ]),
        html.P(id="readout"),
        html.P(id="readout2"),
        html.P(id="readout3"),
        html.P(id="readout4"),
        html.P(id="connection-deleted-readout"),
        html.P(id="element-created-readout"),
    ])
])


@app.callback(
    Output("element-created-readout", "children"),
    Output("element-label-input", "value"),
    Output("element-type-input", "value"),
    Input("element-submit", "n_clicks"),
    State("element-label-input", "value"),
    State("element-type-input", "value"),
)
def create_element(_, label, sd_type):
    if label == "":
        return "need label", label, sd_type
    if sd_type == "":
        return "need type", label, sd_type
    Element(label=label, sd_type=sd_type).save()
    return f"created element '{label}'", "", ""


@app.callback(
    Output("connection-deleted-readout", "children"),
    Input({"type": "delete-connection-button", "index": ALL}, "n_clicks"),
    State({"type": "delete-connection-button", "index": ALL}, "id")
)
def delete_connection(n_clicks, ids):
    print(f"n_clicks is {n_clicks}")
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            pks = id.get("index").split("-to-")
            Connection.objects.get(from_element__pk=pks[0], to_element__pk=pks[1]).delete()
    return f"{ids}"


@app.callback(
    Output("readout4", "children"),
    Input("element-equation-submit", "n_clicks"),
    State("cyto", "tapNodeData"),
    State("element-equation-input", "value"),
)
def submit_equation(n_clicks, nodedata, value):
    if value is None or nodedata is None:
        return "nothing inputted or selected"
    element = Element.objects.get(pk=nodedata.get("id"))
    element.equation = value
    element.save()
    return f"saved equation {value} in {element}"


@app.callback(
    Output("readout3", "children"),
    Input("element-connection-submit", "n_clicks"),
    State("cyto", "tapNodeData"),
    State("element-connection-input", "value")
)
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
    Output("readout2", "children"),
    Input("run-model", "n_clicks"),
    Input("readout4", "children"),
)
def run_model_from_cyto(n_clicks, readout):
    df = run_model()
    return "ran model"


@app.callback(
    Output("element-graph", "figure"),
    Output("element-connections", "children"),
    Output("element-connection-input", "options"),
    Output("element-equation", "children"),
    Output("element-equation-input", "value"),
    Input("cyto", "tapNodeData"),
    Input("readout3", "children"),
    Input("readout4", "children"),
    Input("readout2", "children"),
    Input("connection-deleted-readout", "children"),
)
def update_element_graph(nodedata, readout3, readout4, readout2, connection_deleted_readout):
    fig = go.Figure(layout=go.Layout(template="simple_white"))
    fig.update_xaxes(title_text="Date")
    if nodedata is None:
        return fig, "", "", "", None

    element = Element.objects.get(pk=nodedata.get("id"))

    upstream_elements = Element.objects.filter(downstream_connections__to_element=element)
    upstream_list = html.Ul([html.Li([f"{upstream_element.label} [_E{upstream_element.pk}_]",
                             dbc.Button("Supprimer", id={"type": "delete-connection-button",
                                                         "index": f"{upstream_element.pk}-to-{element.pk}"},
                                        size="sm")])
                             for upstream_element in upstream_elements])

    dropdown_options = Element.objects.exclude(downstream_connections__to_element=element).exclude(pk=element.pk)
    dropdown_list = [possible_element.label for possible_element in dropdown_options]

    equation_text = element.equation
    if equation_text is not None:
        for key_element in Element.objects.all():
            equation_text = equation_text.replace(f"_E{key_element.pk}_", key_element.label)
        equation_text = f"Equation = {equation_text}"

    fig.update_layout(title=element.label)
    df = pd.DataFrame(list(SimulatedDataPoint.objects.filter(element=element).values("date", "value")))

    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["value"]
        ))

    return fig, upstream_list, dropdown_list, equation_text, ""


@app.callback(
    Output("readout", "children"),
    Input("save-positions", "n_clicks"),
    State("cyto", "elements")
)
def save_element_positions(n_clicks, cyto_elements):
    if n_clicks == 0:
        return "not saved yet"

    for cyto_element in cyto_elements:
        if "position" in cyto_element:
            element = Element.objects.get(pk=cyto_element.get("data").get("id"))
            element.x_pos, element.y_pos = cyto_element.get("position").get("x"), cyto_element.get("position").get("y")
            element.save()

    return "saved"


@app.callback(
    Output("cyto", "elements"),
    Input("readout3", "children"),
    Input("readout4", "children"),
    Input("connection-deleted-readout", "children"),
    Input("element-created-readout", "children"),
)
def position_elements(readout3, readout4, *_):
    elements = Element.objects.all()
    nodes = [{"data": {"id": element.pk,
                       "label": element.label,
                       "sd_type": element.sd_type,
                       "sim_input_var": element.sim_input_var,
                       "equation_stored": "yes" if element.equation else "no"},
              "position": {"x": element.x_pos, "y": element.y_pos}}
             for element in elements]

    connections = Connection.objects.all()
    edges = [{"data": {"source": connection.from_element.pk,
                       "target": connection.to_element.pk}}
             for connection in connections]

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

    return nodes + edges + flow_edges

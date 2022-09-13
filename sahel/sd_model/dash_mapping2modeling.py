from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from sahel.models import Variable, Connection, ElementGroup, HouseholdConstantValue, MeasuredDataPoint, \
    SimulatedDataPoint, ForecastedDataPoint, Source, Element
from .model_operations import timer
import time
import pandas as pd
import plotly.graph_objects as go


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
    {"selector": "[!usable]",
     "style": {
         "background-color": "whitesmoke",
         "color": "grey",
         "border-color": "grey",
     }},
    {"selector": "[has_equation = 'no']",
     "style": {
         "line-style": "dashed"
     }},
    {"selector": ".group",
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

app = DjangoDash("mapping2modeling", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div(children=[
    # init div for populate initial values
    html.Div(id="init", hidden=True, children="init"),

    # overlay stuff, all with position:absolute (cannot click through divs in Dash for some reason, z-index not working either)
    html.Div(id="left-sidebar", className="mt-4 ml-4", style={"position": "absolute"}, children=[
        html.H2(className="mb-4 h2", children="Schéma"),
        dbc.Card(className="mb-4", children=[
            dbc.CardBody(className="p-2", children=[
                dbc.FormGroup(className="m-0", children=[
                    dbc.Label("Couches"),
                    dbc.Checklist(
                        id="layers-input",
                        options=[
                            {"label": "Secteurs", "value": "sector", "disabled": True},
                            {"label": "Groupes", "value": "group"},
                            {"label": "Éléments", "value": "element"},
                            {"label": "Variables", "value": "variable"},
                        ],
                        value=["group", "element", "variable"],
                        switch=True,
                    )
                ])
            ])
        ]),
        dbc.Button(className="mb-4", id="download-submit", children="Télécharger SVG", size="sm", color="primary"),
    ]),

    html.Div(id="right-sidebar", className="mt-4 mr-4", style={"position": "absolute", "right": 0, "width": "300px"}),

    # cytoscape underlay with position:absolute
    html.Div(
        style={
            "position": "absolute",
            "top": 0,
            "width": "100%",
            "zIndex": "-1",
        },
        children=cyto.Cytoscape(
            id="cyto",
            layout={"name": "preset", "fit": True},
            style={"height": "1000px", "background-color": "#f8f9fc"},
            stylesheet=stylesheet,
            minZoom=0.2,
            maxZoom=2.0,
            boxSelectionEnabled=True,
            autoRefreshLayout=True,
            responsive=True,
        ),
    ),

    html.Div(id="model-initialized", children="no", hidden=True)
])


# @app.callback(
#     Output("selected-node-id", "children"),
#     Input("cyto", "selectedNodeData"),
#     Input({"type": "select-variable", "index": ALL}, "n_clicks"),
#     State({"type": "select-variable", "index": ALL}, "id"),
# )
# def actually_select_node(selectednodedata, n_clickss, ids):
#     # had to actually write this because Dash Cytoscape selectednodedata doesn't work correctly
#     if not selectednodedata:
#         # if nothing is selected, return nothing
#         return None
#     if all(n_clicks is None for n_clicks in n_clickss):
#         # if nothing has been clicked, return default selected
#         return selectednodedata[-1].get("id")
#     for n_clicks, id, in zip(n_clickss, ids):
#         if n_clicks is not None:
#             selected_pk = id.get("index")
#             print(f"you just clicked on variable {selected_pk}")
#             return selected_pk


@app.callback(
    Output("cyto", "generateImage"),
    Input("download-submit", "n_clicks"),
)
@timer
def download_svg(n_clicks):
    if n_clicks is None:
        raise PreventUpdate
    return {"type": "svg", "action": "download", "filename": "SAMRA_model_schema"}


@app.callback(
    Output("cyto", "stylesheet"),
    Input("layers-input", "value"),
)
def show_layers(layers):
    layers.sort()
    print(layers)
    added_stylesheet = []
    if "group" not in layers:
        added_stylesheet.extend([
            {"selector": ".group",
             "style": {
                 "background-opacity": "0",
                 "border-width": "0",
                 "text-opacity": "0",
             }},
        ])
    if "element" not in layers:
        added_stylesheet.extend([
            {"selector": ".variable",
             "style": {
                 "visibility": "hidden",
             }},
            {"selector": "edge",
             "style": {
                 "visibility": "hidden",
             }},
        ])
    if layers == ["group"]:
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
    Output("cyto", "elements"),
    Input({"type": "select-variable", "index": ALL}, "n_clicks"),
    State({"type": "select-variable", "index": ALL}, "id"),
    State("cyto", "elements"),
)
@timer
def draw_model(n_clickss, ids, cyto_elements):
    print(n_clickss)
    print(ids)
    # if map has not yet been plotted, always update
    if cyto_elements is not None:
        # if no clicks OR nothing clickable, don't update
        if all(n_clicks is None for n_clicks in n_clickss) or not n_clickss:
            raise PreventUpdate

    selected_pk = None
    for n_clicks, id, in zip(n_clickss, ids):
        if n_clicks is not None:
            selected_pk = id.get("index")

    start = time.time()
    variables = Variable.objects.all().values()
    nodes = []
    for variable in variables:
        color = "white"
        usable = True
        if variable.get("sd_type") in ["Variable", "Flow"] and variable.get("equation") is None:
            usable = False

        parent = None
        if variable.get("element_id") is not None:
            parent = f"element_{variable.get('element_id')}"
        elif variable.get("element_group_id") is not None:
            parent = f"group_{variable.get('element_group_id')}"

        nodes.append(
            {"data": {"id": variable.get("id"),
                      "label": variable.get("label"),
                      "sd_type": variable.get("sd_type"),
                      "usable": usable,
                      "parent": parent,
                      "color": color,
                      "hierarchy": "variable"},
             "selected": str(variable.get("id")) == selected_pk,
             "position": {"x": variable.get("x_pos"), "y": variable.get("y_pos")},
             "classes": "variable"}
        )

    print(f"elements took {time.time() - start}")
    start = time.time()

    elements = Element.objects.all().values()
    element_nodes = [
        {"data": {"id": f"element_{element.get('id')}",
                  "label": element.get("label"),
                  "hierarchy": "element"},
         "classes": "element",
         "selected": f"element_{element.get('id')}" == selected_pk}
        for element in elements
    ]
    nodes.extend(element_nodes)

    element_groups = ElementGroup.objects.all().values()
    group_nodes = [
        {"data": {"id": f"group_{element_group.get('id')}",
                  "label": element_group.get("label"),
                  "hierarchy": "group"},
         "classes": "group",
         "selected": f"group_{element_group.get('id')}" == selected_pk,
         "grabbable": False,
         "selectable": True,
         "pannable": True}
        for element_group in element_groups
    ]
    nodes.extend(group_nodes)
    print(f"groups took {time.time() - start}")
    start = time.time()

    connections = Connection.objects.all().select_related("to_element")
    edges = []
    eq_time = 0
    append_time = 0
    eq_read_time = 0
    for connection in connections:
        eq_start = time.time()
        has_equation = "no"
        if connection.to_element is not None:
            if connection.to_element.equation is not None:
                eq_read_start = time.time()
                has_equation = "yes" if f"_E{connection.from_element_id}_" in connection.to_element.equation else "no"
                eq_read_time += time.time() - eq_read_start

        eq_time += time.time() - eq_start
        append_start = time.time()
        edges.append({"data": {"source": connection.from_element_id,
                                "target": connection.to_element_id,
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


@app.callback(
    Output("right-sidebar", "children"),
    Input("cyto", "selectedNodeData"),
    State("cyto", "tapNode"),
)
def right_sidebar(selectednodedata, node):
    # INIT
    print(f"selectednotedata={selectednodedata}")
    children = []
    if node is None or not selectednodedata:
        return children
    nodedata = selectednodedata[-1]
    scenario_pk= "1"
    responseoption_pk = "1"
    admin1 = None

    # GROUP
    if nodedata.get("hierarchy") == "group":
        elementgroup = ElementGroup.objects.get(pk=nodedata.get("id").removeprefix("group_"))
        children.append(html.H4(className="mb-2 h4", children=elementgroup.label))
        children.append(html.H6(className="mb-2 font-italic text-secondary font-weight-light h6", children="GROUPE"))

    # ELEMENT
    elif nodedata.get("hierarchy") == "element":
        element = Element.objects.get_subclass(pk=nodedata.get("id").removeprefix("element_"))

        # label and type
        children.append(html.H4(className="mb-2 h4", children=element.label))
        children.append(html.H6(className="mb-3 font-italic text-secondary font-weight-light h6",
                                children=f"ÉLÉMENT | {element.__class__._meta.verbose_name}"))

        # variables and indicators
        children.append(html.P(className="mb-0 font-weight-bold", children="Variables / Indicateurs"))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        children.extend([
            dbc.Button(
                id={"type": "select-variable", "index": str(variable.pk)},
                className="mb-1", outline=True, color="secondary", size="sm", children=variable.label
            )
            for variable in element.variables.all()
        ])

        # EBs
        children.append(html.P(className="mt-4 mb-0 font-weight-bold", children="Informations Qualitatives"))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))


    # VARIABLE
    elif nodedata.get("hierarchy") == "variable":
        variable = Variable.objects.get(pk=nodedata.get("id"))
        children.append(html.H4(className="mb-2 h4", children=variable.label))
        children.append(html.H6(className="mb-2 font-italic text-secondary font-weight-light h6",
                                children=f"VARIABLE | {variable.get_sd_type_display()}"))

        # graph
        fig = go.Figure(layout=go.Layout(template="simple_white", margin=go.layout.Margin(l=0, r=0, b=0, t=0)))
        fig.update_xaxes(title_text="Date")

        df = pd.DataFrame(SimulatedDataPoint.objects
                          .filter(element=variable, scenario_id=scenario_pk, responseoption_id=responseoption_pk)
                          .values("date", "value"))
        if not df.empty:
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df["value"],
                name="Simulé",
            ))

        if admin1 is None:
            df = pd.DataFrame(MeasuredDataPoint.objects.filter(element=variable).values())
        else:
            df = pd.DataFrame(MeasuredDataPoint.objects.filter(element=variable, admin1=admin1).values())

        if not df.empty:
            source_ids = df["source_id"].drop_duplicates()
            for source_id in source_ids:
                try:
                    source = Source.objects.get(pk=source_id)
                except Source.DoesNotExist:
                    print(f"no source for datapoint in {variable}")
                    continue
                dff = df[df["source_id"] == source_id].groupby("date").mean().reset_index()
                fig.add_trace(go.Scatter(
                    x=dff["date"],
                    y=dff["value"],
                    name=source.title,
                ))
        unit_append = " / mois" if variable.sd_type == "Pulse Input" else ""
        fig.update_layout(
            legend=dict(yanchor="bottom", x=0, y=1),
            showlegend=True,
            yaxis=dict(title=variable.unit + unit_append),
        )
        fig_div = dcc.Graph(figure=fig, id="element-detail-graph", style={"height": "300px"}, className="mb-2")
        children.append(fig_div)

        if variable.sd_type in ["Flow", "Variable"]:
            # connections
            upstream_elements = Variable.objects.filter(downstream_connections__to_element=variable)
            upstream_list = dbc.ListGroup(
                [
                    dbc.ListGroupItem(className="p-1 justify-content-between", children=
                        html.Div(className="d-flex justify-content-between", children=
                            [
                                html.P(style={"font-size": "small"}, children=f"{upstream_element.label} _E{upstream_element.pk}_"),
                                dbc.Button("X",
                                           id={"type": "element-detail-conn-del",
                                               "index": f"{upstream_element.pk}-to-{variable.pk}"},
                                           size="sm",
                                           color="danger",
                                           className="p-1",
                                           outline=True)
                            ],

                        )
                    )
                    for upstream_element in upstream_elements
                ],
                flush=True,
                style={"height": "150px", "overflow-y": "scroll"}
            )

            dropdown_options = Variable.objects.exclude(downstream_connections__to_element=variable).exclude(pk=variable.pk)
            dropdown_list = [
                {"label": possible_element.label, "value": possible_element.label}
                for possible_element in dropdown_options
            ]

            upstream_card = dbc.Card(className="mb-2", children=[
                dbc.CardHeader("Influencé par", className="p-1", style={"font-size": "small"}),
                dbc.CardBody(
                    [
                        upstream_list,
                        dbc.InputGroup(children=[
                            dbc.Select(options=dropdown_list, id="element-detail-conn-input", placeholder="Ajouter une influence", bs_size="sm"),
                            dbc.InputGroupAddon(dbc.Button("Saisir", id="element-detail-conn-submit", size="sm"), addon_type="append")
                        ]),
                    ],
                    style={"padding": "0px"},
                )
            ])
            children.append(upstream_card)

            # equation
            equation_text = variable.equation
            if equation_text is not None:
                for key_element in Variable.objects.all():
                    equation_text = equation_text.replace(f"_E{key_element.pk}_", key_element.label)
                equation_text = f" = {equation_text}"

            equation_card = dbc.Card([
                dbc.CardHeader("Équation", className="p-1", style={"font-size": "small"}),
                dbc.CardBody(className="p-2", children=
                    [
                        html.P(equation_text, id="element-detail-eq-text", style={"font-size": "small", "height": "50px", "overflow-y": "scroll"}),
                        dbc.InputGroup([
                            dbc.Input(value=variable.equation, id="element-detail-eq-input", bs_size="sm"),
                            dbc.InputGroupAddon(dbc.Button("Saisir", id="element-detail-eq-submit", size="sm"), addon_type="append"),
                        ]),

                    ]
                )
            ])
            children.append(equation_card)

        elif variable.sd_type == "Stock":
            # inflows
            inflows_card = dbc.Card(className="mb-4", children=[
                dbc.CardHeader(className="p-1", style={"font-size": "small"}, children="Flux intrants"),
                dbc.CardBody(style={"padding": "0px"}, children=[
                    dbc.ListGroup(
                        [
                            dbc.ListGroupItem(className="p-1 d-flex justify-content-between", style={"font-size": "small"}, children=[
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
            ])
            children.append(inflows_card)

            outflows_card = dbc.Card(className="mb-4", children=[
                dbc.CardHeader(className="p-1", style={"font-size": "small"}, children="Flux sortants"),
                dbc.CardBody(style={"padding": "0px"}, children=[
                    dbc.ListGroup(
                        [
                            dbc.ListGroupItem(className="p-1 d-flex justify-content-between", style={"font-size": "small"}, children=[
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
                                       for potential_outflow in Variable.objects.filter(sd_type="Flow").exclude(sd_sink=variable).exclude(sd_source=variable)
                                   ]),
                        dbc.Button("Saisir", id="element-detail-outflow-submit", size="sm")
                    ])
                ])
            ])
            children.append(outflows_card)

        elif variable.sd_type == "Household Constant":
            try:
                value = variable.householdconstantvalues.get().value
            except HouseholdConstantValue.DoesNotExist:
                value = None
            householdvalue_card = dbc.InputGroup([
                dbc.InputGroupText("Value"),
                dbc.Input(id="householdconstantvalue-input", value=value),
                dbc.Button("Saisir", id="householdconstantvalue-submit")
            ])
            children.append(householdvalue_card)

    if not children:
        return None
    else:
        return dbc.Card(dbc.CardBody(className="p-2", children=children))

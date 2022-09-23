from django_plotly_dash import DjangoDash
from dash import html, dcc, ctx
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from sahel.models import Variable, VariableConnection, ElementGroup, HouseholdConstantValue, MeasuredDataPoint, \
    SimulatedDataPoint, ForecastedDataPoint, Source, Element, ElementConnection, TheoryOfChange, SituationalAnalysis
from .model_operations import timer
import time
import pandas as pd
import plotly.graph_objects as go
from pprint import pprint

stylesheet = [
    # ALL
    # nodes
    {
        "selector": "node",
        "style": {
            "content": "data(label)",
            "background-color": "data(color)",
            "width": 100,
            "height": 100,
            "border-width": 1,
            "text-valign": "top",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": 100,
            "background-opacity": 0.7,
        }
    },
    # edges
    {
        "selector": "edge",
        "style": {
            "curve-style": "unbundled-bezier",
            "control-point-distance": "50px",
            "arrow-scale": 1,
            "target-arrow-shape": "triangle",
        }
    },

    # GROUPS
    # nodes
    {"selector": "node.group",
     "style": {
         "color": "lightgrey",
         "font-size": 40,
         "border-width": 3,
         "border-color": "lightgrey",
         "background-color": "white",
         "z-index": 1,
     }},

    # ELEMENTS
    # nodes
    {"selector": "node.element",
     "style": {
         "font-size": 20,
         "border-width": 2,
         "z-index": 2,
     }},
    {"selector": ".IV",
     "style": {
         # rebeccapurple
         "background-color": "#d9c6ec",
         "border-color": "#66329a",
         "color": "#66329a",
         "line-color": "#9965cd",
         "target-arrow-color": "#9965cd",
     }},
    {"selector": ".SA",
     "style": {
         # chocolate
         "background-color": "#f9e2d2",
         "border-color": "#d2691e",
         "color": "#d2691e",
         "line-color": "#e99b63",
         "target-arrow-color": "#e99b63",
     }},
    {"selector": ".SE",
     "style": {
         "background-color": "#F08080",
         "border-color": "crimson",
         "color": "crimson",
         "line-color": "crimson",
         "target-arrow-color": "crimson",
     }},

    # edges

    # VARIABLES
    # nodes
    {"selector": "node.variable",
     "style": {
         "color": "#505050",
         "border-color": "#505050",
         "text-valign": "center",
         "z-index": 3,
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
    {"selector": "[!usable].variable",
     "style": {
         "background-color": "whitesmoke",
         "color": "grey",
         "border-color": "grey",
     }},

    # edges
    {"selector": "edge.variable",
     "style": {
         "target-arrow-color": "#808080",
         "line-color": "#808080",
         "width": 1,
     }},
    {"selector": "[edge_type = 'Flow']",
     "style": {
         "line-color": "#DCDCDC",
         "target-arrow-shape": "none",
         "mid-target-arrow-shape": "triangle",
         "mid-target-arrow-color": "grey",
         "width": 20,
         "arrow-scale": 0.4,
         "curve-style": "straight",
     }},
    {"selector": "[has_equation = 'no']",
     "style": {
         "line-style": "dashed"
     }},

    # SELECTED
    {"selector": ":selected",
     "style": {
         "border-color": "blue",
         "border-width": 3,
     }},
]

app = DjangoDash("mapping2modeling", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div(children=[
    # INIT
    # init div for populate initial values
    html.Div(id="init", hidden=True, children="init"),

    # OVERLAY
    # overlay stuff, all with position:absolute
    # (cannot click through divs in Dash for some reason, z-index not working either)
    html.Div(id="left-sidebar", className="mt-4 ml-4", style={"position": "absolute"}, children=[
        html.H2(className="mb-4 h2", children="Schéma"),

        # layers
        dbc.Card(className="mb-3", children=[
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

        # colors
        dbc.Card(className="mb-3", children=[
            dbc.CardBody(className="p-2", children=[
                html.P(className="mb-1", children="Couleurs"),
                *[
                    dbc.InputGroup(className="mt-1", size="sm", children=[
                        dbc.InputGroupAddon(addon_type="prepend", children=part.capitalize()),
                        dbc.Select(id=f"color{part}-input")
                    ])
                    for part in ["body", "border", "ring"]
                ],
            ])
        ]),
        dbc.Button(className="mb-3", id="download-submit", children="Télécharger SVG", size="sm", color="primary"),
        html.Br(),
        dbc.Button(className="mb-3", id="add-node-open", children="Ajouter", size="sm", color="primary"),
    ]),

    # MODALS
    # add node
    dbc.Modal(id="add-node-modal", is_open=False, children=[
        dbc.ModalHeader("Ajouter un objet"),
        dbc.ModalBody(children=[
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Classe", addon_type="prepend"),
                dbc.Select(id="add-node-class-input", value="variable", options=[
                    {"label": "Groupe", "value": "group"},
                    {"label": "Élément", "value": "element"},
                    {"label": "Variable", "value": "variable"},
                ]),
            ]),
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Sous-classe", addon_type="prepend"),
                dbc.Select(id="add-node-subclass-input"),
            ]),
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Type", addon_type="prepend"),
                dbc.Select(id="add-node-type-input"),
            ]),
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Label", addon_type="prepend"),
                dbc.Input(id="add-node-label-input"),
            ]),
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Unité", addon_type="prepend"),
                dbc.Select(id="add-node-unit-input"),
            ]),
        ]),
        dbc.ModalFooter(className="d-flex justify-content-end", children=[
            dbc.Button(id="add-node-close", className="ml-2", n_clicks=0, children="Annuler"),
            dbc.Button(id="add-node-submit", className="ml-2", n_clicks=0, color="primary", children="Saisir"),
        ]),
    ]),

    # RIGHT SIDEBAR
    html.Div(id="right-sidebar", className="mt-4 mr-4", style={"position": "absolute", "right": 0, "width": "300px"}),

    # CYTO
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
            layout={"name": "preset", "fit": False},
            style={"height": "1000px", "background-color": "#f8f9fc"},
            stylesheet=stylesheet,
            minZoom=0.2,
            maxZoom=2.0,
            boxSelectionEnabled=True,
            autoRefreshLayout=True,
            responsive=True,
            zoom=0.5,
        ),
    ),
])


@app.callback(
    # color dropdowns
    *[
        [Output(f"color{part}-input", "options"), Output(f"color{part}-input", "value")]
        for part in ["body", "border", "ring"]
    ],
    Input("init", "children"),
)
def populate_initial(_):
    options = [{"value": "default", "label": "---"}]
    options.extend([
        {"value": field, "label": field}
        for field in SituationalAnalysis.SA_FIELDS
    ])
    value = "default"
    return options, value, options, value, options, value


@app.callback(
    Output("add-node-modal", "is_open"),
    Input("add-node-open", "n_clicks"),
    Input("add-node-close", "n_clicks"),
    Input("add-node-submit", "n_clicks"),
    State("add-node-modal", "is_open")
)
def add_node_modal(open_clicks, close_clicks, submit_clicks, is_open):
    if open_clicks or close_clicks or submit_clicks:
        return not is_open
    return is_open


@app.callback(
    Output("add-node-subclass-input", "options"),
    Output("add-node-subclass-input", "value"),
    Output("add-node-subclass-input", "disabled"),
    Input("add-node-class-input", "value")
)
def add_node_subclass(class_input):
    options = []
    value = None
    disabled = True
    if class_input == "group":
        pass
    elif class_input == "element":
        options = [
            {"label": "Analyse de situation", "value": "situationalanalysis"},
            {"label": "Théorie de changement", "value": "theoryofchange"}
        ]
        value = "situationalanalysis"
        disabled = False
    elif class_input == "variable":
        pass
    return options, value, disabled


@app.callback(
    Output("add-node-type-input", "options"),
    Output("add-node-type-input", "value"),
    Output("add-node-type-input", "disabled"),
    Input("add-node-class-input", "value"),
    Input("add-node-subclass-input", "value"),
)
def add_node_type(class_input, subclass_input):
    options = []
    value = None
    disabled = True
    if class_input == "groupe":
        pass
    elif class_input == "variable":
        options = [
            {"label": sd_type[1], "value": sd_type[0]}
            for sd_type in Variable.SD_TYPES
        ]
        value = "Variable"
        disabled = False
    elif subclass_input == "theoryofchange":
        options = [
            {"label": tc_type[1], "value": tc_type[0]}
            for tc_type in TheoryOfChange.TOC_TYPES
        ]
        value = TheoryOfChange.INTERVENTION
        disabled = False
    elif subclass_input == "situationalanalysis":
        options = [
            {"label": sa_type[1], "value": sa_type[0]}
            for sa_type in SituationalAnalysis.SA_TYPES
        ]
        value = SituationalAnalysis.SITUATIONAL_ANALYSIS
    return options, value, disabled


@app.callback(
    Output("add-node-unit-input", "options"),
    Output("add-node-unit-input", "value"),
    Output("add-node-unit-input", "disabled"),
    Input("add-node-class-input", "value"),
)
def add_node_unit(class_input):
    options = []
    value = None
    disabled = True
    if class_input == "variable":
        options = [
            {"label": sd_unit[1], "value": sd_unit[0]}
            for sd_unit in Variable.UNIT_OPTIONS
        ]
        value = "tête / mois"
        disabled = False
    return options, value, disabled


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
    [
        Input(f"color{part}-input", "value")
        for part in ["body", "border", "ring"]
    ]
)
def show_layers(layers, colorbody_field, colorborder_field, colorring_field):
    print(f"colorbody_field is {colorbody_field}")
    # LAYERS
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
            {"selector": ".element",
             "style": {
                 "background-opacity": "0",
                 "border-width": "0",
                 "text-opacity": "0",
             }},
        ])
    if "variable" not in layers:
        added_stylesheet.extend([
            {"selector": ".variable",
             "style": {
                 "visibility": "hidden",
             }},
            {"selector": ".element",
             "style": {
                 "text-valign": "center",
             }}

        ])

    # COLOR
    # map general values to colors
    value2color = {}
    if colorbody_field == "status":
        print("coloring by status")
        value2color.update({
            SituationalAnalysis.SA_STATUS_GOOD: "green",
            SituationalAnalysis.SA_STATUS_OK: "yellow",
            SituationalAnalysis.SA_STATUS_BAD: "red",
        })
    elif colorbody_field == "trend":
        value2color.update({
            SituationalAnalysis.SA_TREND_IMPROVING: "green",
            SituationalAnalysis.SA_TREND_STAGNANT: "yellow",
            SituationalAnalysis.SA_TREND_WORSENING: "red",
        })
    elif colorbody_field == "resilience":
        value2color.update({
            SituationalAnalysis.SA_RES_HIGH: "green",
            SituationalAnalysis.SA_RES_MED: "yellow",
            SituationalAnalysis.SA_RES_LOW: "red",
        })

    # body
    if colorbody_field != "default":
        print(f"value2color is {value2color}")
        print(f"choices are {SituationalAnalysis._meta.get_field(colorbody_field).choices}")
        added_stylesheet.extend([
            {
                "selector": f"[{colorbody_field} = '{choice[0]}']",
                "style": {
                    "background-color": value2color.get(choice[0])
                }
            }
            for choice in SituationalAnalysis._meta.get_field(colorbody_field).choices
        ])

    # border
    if colorborder_field != "default":
        added_stylesheet.extend([
            {
                "selector": f"[{colorborder_field} = '{choice[0]}']",
                "style": {
                    "border-color": value2color.get(choice[0])
                }
            }
            for choice in SituationalAnalysis._meta.get_field(colorborder_field).choices
        ])

    return stylesheet + added_stylesheet


@app.callback(
    Output("cyto", "elements"),

    # INPUTS

    # relationship modification
    Input({"type": "select-node", "index": ALL}, "n_clicks"),
    Input({"type": "delete-node", "index": ALL}, "n_clicks"),
    Input({"type": "remove-node", "index": ALL}, "n_clicks"),
    Input({"type": "parentchild-submit", "index": ALL}, "n_clicks"),

    # add node
    Input("add-node-submit", "n_clicks"),

    # change field
    [
        Input({"type": f"{field}-input", "index": ALL}, "value")
        for field in SituationalAnalysis.SA_FIELDS
    ],

    # delete connection
    Input({"type": "delete-connection", "index": ALL}, "n_clicks"),

    # STATES

    # relationship modification
    State({"type": "select-node", "index": ALL}, "id"),
    State({"type": "delete-node", "index": ALL}, "id"),
    State({"type": "remove-node", "index": ALL}, "id"),
    State({"type": "parentchild-submit", "index": ALL}, "id"),
    State({"type": "parentchild-input", "index": ALL}, "value"),

    # add node
    State("add-node-class-input", "value"),
    State("add-node-subclass-input", "value"),
    State("add-node-type-input", "value"),
    State("add-node-label-input", "value"),
    State("add-node-unit-input", "value"),
    State("add-node-modal", "is_open"),

    # change field
    [
        State({"type": f"{field}-input", "index": ALL}, "id")
        for field in SituationalAnalysis.SA_FIELDS
    ],

    # delete connections
    State({"type": "delete-connection", "index": ALL}, "id"),

    # current elements read
    State("cyto", "elements"),
)
@timer
def draw_model(
        # INPUTS

        # relationship modification
        select_clicks,
        delete_clicks,
        remove_clicks,
        parentchild_clicks,

        # add node
        add_node_clicks,

        # change field
        status_field_input,
        trend_field_input,
        resilience_field_input,
        vulnerability_field_input,

        # delete connection
        delete_connection_clicks,

        # STATES

        # relationship modification
        select_ids,
        delete_ids,
        remove_ids,
        parentchild_ids,
        parentchild_input,

        # add node
        class_input,
        subclass_input,
        type_input,
        label_input,
        unit_input,
        add_node_modal_is_open,

        # change fields
        status_field_id,
        trend_field_id,
        resilience_field_id,
        vulnerability_field_id,

        # delete connection
        delete_connection_ids,

        # current elements read
        cyto_elements: list[dict],
):
    # SELECT NODE
    for n_clicks, id in zip(select_clicks, select_ids):
        if n_clicks is not None:
            selected_id = id.get("index")
            for cyto_element in cyto_elements:
                if cyto_element.get("data").get("id") == selected_id:
                    cyto_element.update({"selected": True})
                else:
                    cyto_element.update({"selected": False})
            return cyto_elements

    # DELETE NODE
    # there is a Dash Cytoscape bug where the child nodes also get removed when the parent is removed
    for n_clicks, id in zip(delete_clicks, delete_ids):
        if n_clicks is not None:
            deleted_id = id.get("index")
            if "element" in deleted_id:
                Element.objects.get(pk=deleted_id.removeprefix("element_")).delete()
            elif "group" in deleted_id:
                ElementGroup.objects.get(pk=deleted_id.removeprefix("group_")).delete()
            updated_cyto_elements = []
            for cyto_element in cyto_elements:
                if cyto_element.get("data").get("parent") == deleted_id:
                    cyto_element.get("data").update({"parent": None})
                if cyto_element.get("data").get("id") != deleted_id:
                    updated_cyto_elements.append(cyto_element)
            return updated_cyto_elements

    # REMOVE NODE
    for n_clicks, id in zip(remove_clicks, remove_ids):
        if n_clicks is not None:
            parent_child_ids = id.get("index").split("-contains-")
            parent_id, child_id = parent_child_ids[0], parent_child_ids[1]
            if "element" in child_id:
                element = Element.objects.get(pk=child_id.removeprefix("element_"))
                element.element_group = None
                element.save()
            elif "variable" in child_id:
                variable = Variable.objects.get(pk=child_id.removeprefix("variable_"))
                variable.element = None
                variable.save()
            for cyto_element in cyto_elements:
                if cyto_element.get("data").get("id") == child_id.removeprefix("variable_"):
                    cyto_element.get("data").update({"parent": None})
            return cyto_elements

    # CONNECT PARENT
    for n_clicks, id in zip(parentchild_clicks, parentchild_ids):
        if n_clicks is not None:
            if id.get("index").startswith("child-"):
                child_id = id.get("index").removeprefix("child-")
                parent_class_str = "group"
                if child_id.startswith("element_"):
                    element = Element.objects.get(pk=child_id.removeprefix("element_"))
                    element.element_group_id = parentchild_input[0]
                    element.save()
                    parent_class_str = "group"
                elif child_id.startswith("variable_"):
                    variable = Variable.objects.get(pk=child_id.removeprefix("variable_"))
                    variable.element_id = parentchild_input[0]
                    variable.save()
                    parent_class_str = "element"
                for cyto_element in cyto_elements:
                    if cyto_element.get("data").get("id") == child_id.removeprefix("variable_"):
                        cyto_element.get("data").update({"parent": f"{parent_class_str}_{parentchild_input[0]}"})
            return cyto_elements

    # ADD NODE
    if add_node_clicks > 0 and add_node_modal_is_open:
        if class_input == "group":
            element_group = ElementGroup(label=label_input)
            element_group.save()
            cyto_elements.append(
                {"data": {"id": f"group_{element_group.pk}",
                          "label": element_group.label,
                          "hierarchy": "group"},
                 "classes": "group",
                 "grabbable": False,
                 "selectable": True,
                 "pannable": True}
            )
            return cyto_elements
        elif class_input == "element":
            element = None
            if subclass_input == "situationalanalysis":
                element = SituationalAnalysis(label=label_input, element_type=type_input).save()
            elif subclass_input == "theoryofchange":
                element = TheoryOfChange(label=label_input, element_type=type_input).save()
            element.save()
            cyto_elements.append(
                {"data": {"id": f"element_{element.pk}",
                          "label": element.label,
                          "hierarchy": "element",
                          "parent": f"group_{element.element_group_id}"},
                 "classes": f"element {element.element_type}"}
            )
        elif class_input == "variable":
            Variable(label=label_input, sd_type=type_input, unit=unit_input).save()

    # CHANGE FIELD
    if status_field_input:
        for field in SituationalAnalysis.SA_FIELDS:
            if field == "status":
                value, id = status_field_input, status_field_id
            elif field == "trend":
                value, id = trend_field_input, trend_field_id
            elif field == "resilience":
                value, id = resilience_field_input, resilience_field_id
            elif field == "vulnerability":
                value, id = vulnerability_field_input, vulnerability_field_id
            else:
                value, id = None, None

            value = value[0]
            id = id[0]

            element = SituationalAnalysis.objects.get(pk=id.get("index"))
            old_value = getattr(element, field)

            if value != old_value:
                setattr(element, field, value)
                element.save()

    # DELETE CONNECTION
    for n_clicks, id in zip(delete_connection_clicks, delete_connection_ids):
        if n_clicks is not None:
            from_element_pk, to_element_pk = [pk.removeprefix("element_") for pk in id.get("index").split("-to-")]
            print(ElementConnection.objects.get(from_element_id=from_element_pk, to_element_id=to_element_pk))
            cyto_elements = [
                cyto_element
                for cyto_element in cyto_elements
                if not (cyto_element.get("data").get("source") == f"element_{from_element_pk}" and
                        cyto_element.get("data").get("target") == f"element_{to_element_pk}")
            ]
            return cyto_elements

    if cyto_elements is not None:
        raise PreventUpdate

    ## INITIAL RUN
    # init
    start = time.time()
    variables = Variable.objects.all().values()
    cyto_elements = []

    # VARIABLES
    # nodes
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

        cyto_elements.append(
            {"data": {"id": variable.get("id"),
                      "label": variable.get("label"),
                      "sd_type": variable.get("sd_type"),
                      "usable": usable,
                      "parent": parent,
                      "color": color,
                      "hierarchy": "variable"},
             "position": {"x": variable.get("x_pos"), "y": variable.get("y_pos")},
             "classes": "variable"}
        )

    # connections
    connections = VariableConnection.objects.all().select_related("to_variable")
    for connection in connections:
        has_equation = "no"
        if connection.to_variable is not None:
            if connection.to_variable.equation is not None:
                has_equation = "yes" if f"_E{connection.from_variable_id}_" in connection.to_variable.equation else "no"

        cyto_elements.append({
            "data": {
                "source": connection.from_variable_id,
                "target": connection.to_variable_id,
                "has_equation": has_equation
            },
            "classes": "variable"
        })

    # variable flows
    stocks = Variable.objects.filter(sd_type="Stock").prefetch_related("inflows", "outflows")
    for stock in stocks:
        for inflow in stock.inflows.all():
            has_equation = "no" if inflow.equation is None else "yes"
            cyto_elements.append(
                {"data": {"source": inflow.pk,
                          "target": stock.pk,
                          "has_equation": has_equation,
                          "edge_type": "Flow"},
                 "classes": "variable"}
            )
        for outflow in stock.outflows.all():
            has_equation = "no" if outflow.equation is None else "yes"
            cyto_elements.append(
                {"data": {"source": stock.pk,
                          "target": outflow.pk,
                          "has_equation": has_equation,
                          "edge_type": "Flow"},
                 "classes": "variable"}
            )

    # ELEMENTS
    # nodes
    cyto_elements.extend([
        {
            "data": {
                "id": f"element_{element.pk}",
                "label": element.label,
                "hierarchy": "element",
                "parent": f"group_{element.element_group_id}",
                **{
                    field: getattr(element, field, None)
                    for field in SituationalAnalysis.SA_FIELDS
                },
            },
            "classes": f"element {element.element_type}"
        }
        for element in Element.objects.all().select_subclasses()
    ])

    # connections
    cyto_elements.extend([
        {
            "data": {
                "source": f"element_{connection.from_element_id}",
                "target": f"element_{connection.to_element_id}"
            },
            "classes": f"element {Element.objects.get_subclass(pk=connection.from_element_id).element_type}"
        }
        for connection in ElementConnection.objects.all()
    ])

    # GROUPS
    element_groups = ElementGroup.objects.all().values()
    group_nodes = [
        {"data": {"id": f"group_{element_group.get('id')}",
                  "label": element_group.get("label"),
                  "hierarchy": "group"},
         "classes": "group",
         "grabbable": False,
         "selectable": True,
         "pannable": True}
        for element_group in element_groups
    ]
    cyto_elements.extend(group_nodes)

    return cyto_elements


@app.callback(
    Output("right-sidebar", "children"),
    Input("cyto", "selectedNodeData"),
    Input("cyto", "elements"),
)
@timer
def right_sidebar(selectednodedata, _):
    # INIT
    children = []
    if not selectednodedata:
        return children
    nodedata = selectednodedata[-1]
    scenario_pk = "1"
    responseoption_pk = "1"
    admin1 = None

    # GROUP
    if "group" in nodedata.get("id"):
        elementgroup = ElementGroup.objects.get(pk=nodedata.get("id").removeprefix("group_"))

        # label and type
        children.append(html.H4(className="mb-2 h4", children=elementgroup.label))
        children.append(html.H6(className="mb-2 font-italic text-secondary font-weight-light h6", children="GROUPE"))

        # children
        children.append(html.P(className="mb-0 font-weight-bold", children="Éléments"))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        children.extend([
            dbc.Button(
                id={"type": "select-node", "index": f"element_{element.pk}"},
                className="mb-1 mr-1", outline=True, color="secondary", size="sm", children=element.label
            )
            for element in elementgroup.elements.all()
        ])

        # delete
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        children.append(
            dbc.Button(
                id={"type": "delete-node", "index": nodedata.get("id")},
                className="mb-2 font-italic", size="sm", outline=True, color="danger", children="Supprimer groupe"
            )
        )

    # ELEMENT
    elif nodedata.get("hierarchy") == "element":
        element = Element.objects.get_subclass(pk=nodedata.get("id").removeprefix("element_"))

        # label and type
        children.append(html.H4(className="mb-2 h4", children=element.label))
        children.append(html.H6(className="mb-3 font-italic text-secondary font-weight-light h6",
                                children=f"ÉLÉMENT | {element.__class__._meta.verbose_name} | "
                                         f"{element.get_element_type_display()}"))

        # parent
        children.append(
            html.Div(className="mb-3", children=[
                html.P(className="mb-1 mr-1 font-weight-bold d-inline", children="Groupe:"),
                dbc.ButtonGroup(className="mb-1", size="sm", children=[
                    dbc.Button(
                        id={"type": "select-node", "index": f"group_{element.element_group_id}"},
                        outline=True, color="secondary", children=element.element_group.label,
                    ),
                    dbc.Button(
                        id={"type": "remove-node",
                            "index": f"group_{element.element_group_id}-contains-element_{element.pk}"},
                        outline=True, color="danger", children="x"
                    )
                ])
                if element.element_group is not None else
                dbc.InputGroup(size="sm", children=[
                    dbc.Select(
                        id={"type": "parentchild-input", "index": "only_one"}, bs_size="sm",
                        options=[{"label": elementgroup.label, "value": elementgroup.pk}
                                 for elementgroup in ElementGroup.objects.all()],
                    ),
                    dbc.InputGroupAddon(addon_type="append", children=dbc.Button(
                        id={"type": "parentchild-submit", "index": f"child-element_{element.pk}"}, children="Saisir"
                    ))
                ]),
            ])
        )

        # children
        children.append(html.P(className="mb-0 font-weight-bold", children="Variables / Indicateurs"))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        children.extend([
            dbc.Button(
                id={"type": "select-node", "index": str(variable.pk)},
                className="mb-1 mr-1", outline=True, color="secondary", size="sm", children=variable.label
            )
            for variable in element.variables.all()
        ])

        # upstream
        children.append(html.P(className="mb-0 font-weight-bold", children="Éléments en amont"))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        children.extend([
            dbc.ButtonGroup(className="mb-1 mr-1", size="sm", children=[
                dbc.Button(
                    id={"type": "select-node", "index": f"element_{upstream_element.pk}"},
                    outline=True, color="secondary", children=upstream_element.label
                ),
                dbc.Button(
                    id={"type": "delete-connection",
                        "index": f"element_{upstream_element.pk}-to-element_{element.pk}"},
                    outline=True, color="danger", children="x"
                )
            ])
            for upstream_element in Element.objects.filter(downstream_connections__to_element=element)
        ])

        # status, trend, resilience, vulnerability for SA only
        if isinstance(element, SituationalAnalysis):
            children.append(html.P(className="mt-3 mb-0 font-weight-bold", children="Characteristics"))
            children.append(html.Hr(className="mb-2 mt-1 mx-0"))
            children.extend([
                dbc.InputGroup(className="mb-2", size="sm", children=[
                    dbc.InputGroupAddon(addon_type="prepend", children=field.capitalize()),
                    dbc.Select(
                        id={"type": f"{field}-input", "index": element.pk},
                        options=[
                            {"value": choice[0], "label": choice[1]}
                            for choice in SituationalAnalysis._meta.get_field(field).choices
                        ],
                        value=getattr(element, field)
                    )
                ])
                for field in SituationalAnalysis.SA_FIELDS
            ])

        # EBs
        children.append(html.P(className="mt-4 mb-0 font-weight-bold", children="Informations Qualitatives"))
        children.append(html.Hr(className="mb-4 mt-1 mx-0"))

        # delete
        children.append(
            dbc.Button(
                id={"type": "delete-node", "index": nodedata.get("id")},
                className="mb-2 font-italic", size="sm", outline=True, color="danger", children="Supprimer élément"
            )
        )

    # VARIABLE
    elif nodedata.get("hierarchy") == "variable":
        variable = Variable.objects.get(pk=nodedata.get("id"))

        # label and type
        children.append(html.H4(className="mb-2 h4", children=variable.label))
        children.append(html.H6(className="mb-2 font-italic text-secondary font-weight-light h6",
                                children=f"VARIABLE | {variable.get_sd_type_display()}"))

        # parent
        children.append(
            html.Div(className="mb-3", children=[
                html.P(className="mb-1 mr-1 font-weight-bold d-inline", children="Élément:"),
                dbc.ButtonGroup(className="mb-1", size="sm", children=[
                    dbc.Button(
                        id={"type": "select-node", "index": f"element_{variable.element_id}"},
                        outline=True, color="secondary", children=variable.element.label,
                    ),
                    dbc.Button(
                        id={"type": "remove-node",
                            "index": f"element_{variable.element_id}-contains-variable_{variable.pk}"},
                        outline=True, color="danger", children="x"
                    )
                ])
                if variable.element is not None else
                dbc.InputGroup(size="sm", children=[
                    dbc.Select(
                        id={"type": "parentchild-input", "index": "only_one"}, bs_size="sm",
                        options=[{"label": element.label, "value": element.pk}
                                 for element in Element.objects.all()],
                    ),
                    dbc.InputGroupAddon(addon_type="append", children=dbc.Button(
                        id={"type": "parentchild-submit", "index": f"child-variable_{variable.pk}"}, children="Saisir"
                    ))
                ]),
            ])
        )

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
                {"label": possible_element.label, "value": possible_element.label}
                for possible_element in dropdown_options
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
            children.append(equation_card)

        elif variable.sd_type == "Stock":
            # inflows
            inflows_card = dbc.Card(className="mb-4", children=[
                dbc.CardHeader(className="p-1", style={"font-size": "small"}, children="Flux intrants"),
                dbc.CardBody(style={"padding": "0px"}, children=[
                    dbc.ListGroup(
                        [
                            dbc.ListGroupItem(className="p-1 d-flex justify-content-between",
                                              style={"font-size": "small"}, children=[
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
                        dbc.Select(id="element-detail-inflow-input", bs_size="sm",
                                   placeholder="Ajouter un flux entrant",
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
                            dbc.ListGroupItem(className="p-1 d-flex justify-content-between",
                                              style={"font-size": "small"}, children=[
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
                        dbc.Select(id="element-detail-outflow-input", bs_size="sm",
                                   placeholder="Ajouter un flux sortant",
                                   options=[
                                       {"label": potential_outflow.label, "value": potential_outflow.pk}
                                       for potential_outflow in
                                       Variable.objects.filter(sd_type="Flow").exclude(sd_sink=variable).exclude(
                                           sd_source=variable)
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

from django_plotly_dash import DjangoDash
from dash import html, dcc, ctx
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from sahel.models import Variable, VariableConnection, ElementGroup, HouseholdConstantValue, MeasuredDataPoint, \
    SimulatedDataPoint, ForecastedDataPoint, Source, Element, ElementConnection, TheoryOfChange, SituationalAnalysis, \
    Story, VariablePosition
from .model_operations import timer
import time
import pandas as pd
import plotly.graph_objects as go
from pprint import pprint
from .mapping_styles import stylesheet, fieldvalue2color, partname2cytokey
from django.db.models import Prefetch
import json

DEFAULT_STORY_PK = "1"

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
                    for part in ["body", "border"]
                ],
            ])
        ]),

        # storylines
        dbc.Card(className="mb-3", children=[
            dbc.CardBody(className="p-2", children=[
                html.P(className="mb-1", children="Histoires"),
                dbc.Select(id="story-input", className="mb-1", bs_size="sm"),
            ])
        ]),
        dbc.Button(className="mb-3", id="download-submit", children="Télécharger SVG", size="sm", color="primary"),
        html.Br(),
        dbc.Button(className="mb-3", id="add-node-open", children="Ajouter", size="sm", color="primary"),
        html.Br(),
        dbc.Button(className="mb-3", id="save-positions", children="Sauvegarder", size="sm", color="primary"),
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

    # READOUTS
    html.P(id="save-positions-readout", hidden=True),
    html.P(id="current-story", hidden=True, children="init"),
    dcc.Store(id="store"),
])


@app.callback(
    Output("save-positions-readout", "children"),
    Input("save-positions", "n_clicks"),
    State("cyto", "elements"),
    State("current-story", "children")
)
@timer
def save_node_positions(n_clicks, cyto_elements, story_pk):
    if n_clicks is None:
        raise PreventUpdate

    old_positions = {str(position.get("variable_id")): position
                     for position in VariablePosition.objects.filter(story_id=story_pk).values()}

    objs = []
    for cyto_element in cyto_elements:
        if "position" in cyto_element and "hidden" not in cyto_element.get("classes"):
            pk = cyto_element.get("data").get("id")
            new_x, new_y = cyto_element.get('position').get("x"), cyto_element.get('position').get("y")
            try:
                old_x, old_y = old_positions.get(str(pk)).get("x_pos"), old_positions.get(str(pk)).get("y_pos")
            except AttributeError:
                old_x, old_y = None, None
            # if pk == "102":
            #     print(f"{old_x=}, {new_x=}")
            #     pprint(cyto_element)
            if old_x != new_x or old_y != new_y:

                try:
                    position = VariablePosition.objects.get(variable_id=pk, story_id=story_pk)
                    print(f"MOVED EXISTING {position}")
                    position.x_pos, position.y_pos = new_x, new_y
                    objs.append(position)
                except VariablePosition.DoesNotExist:
                    print(f"adding new position for {pk}")
                    VariablePosition(variable_id=pk, story_id=story_pk, x_pos=new_x, y_pos=new_y).save()

    VariablePosition.objects.bulk_update(objs, ["x_pos", "y_pos"])


@app.callback(
    # color dropdowns
    *[[Output(f"color{part}-input", "options"), Output(f"color{part}-input", "value")]
      for part in ["body", "border"]],
    Output("story-input", "options"),
    Output("story-input", "value"),
    Input("init", "children"),
)
def populate_initial(_):
    # colors
    color_options = [{"value": "default", "label": "---"}]
    color_options.extend([
        {"value": field, "label": field}
        for field in SituationalAnalysis.SA_FIELDS
    ])
    color_value = "default"

    # storyline
    story_options = [
        {"value": story.pk, "label": story.name}
        for story in Story.objects.all()
    ]
    story_value = DEFAULT_STORY_PK

    return color_options, color_value, color_options, color_value, story_options, story_value


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
        for part in ["body", "border"]
    ]
)
def show_layers(layers, colorbody_field, colorborder_field):
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


    # body
    for part_field, part_name in zip([colorbody_field, colorborder_field], ["body", "border"]):
        print(f"part_field is {part_field}, part_name is {part_name}")
        if part_field != "default":
            print(f"choices are {SituationalAnalysis._meta.get_field(part_field).choices}")
            # first set all SAs to grey
            added_stylesheet.append({
                "selector": ".SA",
                "style": {
                    partname2cytokey.get(part_name): "grey",
                }
            })
            # then color for those with field
            added_stylesheet.extend([
                {
                    "selector": f"[{part_field} = '{choice[0]}']",
                    "style": {
                        partname2cytokey.get(part_name): fieldvalue2color.get(part_field).get(choice[0]).get(part_name)
                    }
                }
                for choice in SituationalAnalysis._meta.get_field(part_field).choices
            ])

    return stylesheet + added_stylesheet


def append_cyto_iteration(cyto_elements: [dict], new_iteration: int):
    updated_cyto_elements = []
    for obj in cyto_elements:
        data = obj.get("data")
        if "id" in data:
            data.update({
                "id": f"{data.get('id')}_iteration{new_iteration}",
                "label": f"{data.get('label')} I{new_iteration}"
            })
        elif "source" in data:
            data.update({
                "source": f"{data.get('source')}_iteration{new_iteration}",
                "target": f"{data.get('source')}_iteration{new_iteration}"
            })
        if "parent" in data:
            data.update({"parent": f"{data.get('parent')}_iteration{new_iteration}"})
    return cyto_elements


@app.callback(
    # OUTPUTS
    Output("cyto", "elements"),
    Output("current-story", "children"),
    Output("store", "data"),

    # INPUTS
    # relationship modification
    Input({"type": "select-node", "index": ALL}, "n_clicks"),
    Input({"type": "delete-node", "index": ALL}, "n_clicks"),
    Input({"type": "remove-node", "index": ALL}, "n_clicks"),
    Input({"type": "parentchild-submit", "index": ALL}, "n_clicks"),
    # add node
    Input("add-node-submit", "n_clicks"),
    # change field
    [Input({"type": f"{field}-input", "index": ALL}, "value")
     for field in SituationalAnalysis.SA_FIELDS],
    # delete connection
    Input({"type": "delete-connection", "index": ALL}, "n_clicks"),
    # add connection
    Input({"type": "add-connection-submit", "index": ALL}, "n_clicks"),
    # story
    Input("story-input", "value"),
    # element store
    Input("store", "data"),

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
    [State({"type": f"{field}-input", "index": ALL}, "id")
     for field in SituationalAnalysis.SA_FIELDS],
    # delete connections
    State({"type": "delete-connection", "index": ALL}, "id"),
    # add connections
    State({"type": "add-connection-submit", "index": ALL}, "id"),
    State({"type": "add-connection-input", "index": ALL}, "value"),
    # story
    State("current-story", "children"),
    # current elements read
    State("cyto", "elements"),
)
@timer
def draw_model(
        # INPUTS
        # relationship modification
        select_clicks, delete_clicks, remove_clicks, parentchild_clicks,
        # add node
        add_node_clicks,
        # change field
        status_field_input, trend_field_input, resilience_field_input, vulnerability_field_input,
        # delete connection
        delete_connection_clicks,
        # add connection
        add_connection_clicks,
        # story
        story_pk,
        # element store
        cyto_elements_store,

        # STATES
        # relationship modification
        select_ids, delete_ids, remove_ids, parentchild_ids, parentchild_input,
        # add node
        class_input, subclass_input, type_input, label_input, unit_input, add_node_modal_is_open,
        # change fields
        status_field_id, trend_field_id, resilience_field_id, vulnerability_field_id,
        # delete connection
        delete_connection_ids,
        # add connection
        add_connection_ids, add_connection_input,
        # story
        current_story_pk,
        # current elements read
        cyto_elements: list[dict],
):
    print("TOP OF REDRAW")
    print(f"{type(cyto_elements_store)}")
    if cyto_elements_store is not None: return json.loads(cyto_elements_store), current_story_pk, None

    # SELECT NODE
    for n_clicks, id in zip(select_clicks, select_ids):
        if n_clicks is not None:
            selected_id = id.get("index")
            print(f"clicked on {selected_id}")
            display_element = {}
            for cyto_element in cyto_elements:
                if cyto_element.get("data").get("id") == selected_id:
                    cyto_element.update({"selected": True})
                    display_element = cyto_element
                else:
                    cyto_element.update({"selected": False})
            return [{}], current_story_pk, json.dumps(cyto_elements)

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
            return [{}], current_story_pk, json.dumps(cyto_elements)

    # REMOVE NODE
    for n_clicks, id in zip(remove_clicks, remove_ids):
        if n_clicks is not None:
            display_element = {}
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
                    display_element = cyto_element
            return [{}], current_story_pk, json.dumps(cyto_elements)

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
            return [{}], current_story_pk, json.dumps(cyto_elements)

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
            return [{}], current_story_pk, json.dumps(cyto_elements)
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
            return [{}], current_story_pk, json.dumps(cyto_elements)
        elif class_input == "variable":
            variable = Variable(label=label_input, sd_type=type_input, unit=unit_input)
            variable.save()
            cyto_elements.append({
                "data": {
                    "id": str(variable.pk),
                    "label": variable.label,
                    "sd_type": variable.sd_type,
                    "usable": False,
                    "hierarchy": "variable"},
                "position": {"x": 0.0, "y": 0.0},
                "classes": "variable"
            })
            return [{}], current_story_pk, json.dumps(cyto_elements)

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
            ElementConnection.objects.get(from_element_id=from_element_pk, to_element_id=to_element_pk).delete()
            cyto_elements = [
                cyto_element
                for cyto_element in cyto_elements
                if not (cyto_element.get("data").get("source") == f"element_{from_element_pk}" and
                        cyto_element.get("data").get("target") == f"element_{to_element_pk}")
            ]
            return [{}], current_story_pk, json.dumps(cyto_elements)

    # ADD CONNECTION
    for n_clicks, id in zip(add_connection_clicks, add_connection_ids):
        if n_clicks is not None:
            to_element_pk = id.get("index").removeprefix("to-element_")
            from_element_pk = add_connection_input[0].removeprefix("element_")
            cyto_elements.append({
                "data": {
                    "source": f"element_{from_element_pk}",
                    "target": f"element_{to_element_pk}",
                },
                "classes": f"element {Element.objects.get_subclass(pk=from_element_pk).element_type}",
            })
            ElementConnection(to_element_id=to_element_pk, from_element_id=from_element_pk).save()
            return [{}], current_story_pk,  json.dumps(cyto_elements)

    if current_story_pk == story_pk:
        raise PreventUpdate

    ## CHANGE VIEW
    # init
    print("redrawing whole model")

    cyto_elements = []
    element_pks_in_story = [obj.get("id") for obj in Element.objects.filter(stories=story_pk).values()]

    # VARIABLES
    # nodes
    queryset = VariablePosition.objects.filter(story_id=story_pk)
    variables = Variable.objects.all().prefetch_related(Prefetch(
        "positions", queryset=queryset, to_attr="story_position"
    ))

    variable_pks = [variable.pk for variable in variables]
    for variable in variables:
        color = "white"
        usable = True
        if variable.sd_type in ["Variable", "Flow"] and variable.equation is None:
            usable = False

        parent = None
        if variable.element_id is not None:
            parent = f"element_{variable.element_id}"

        if story_pk == DEFAULT_STORY_PK or variable.element_id in element_pks_in_story:
            in_story = True
        else:
            in_story = False

        class_append = ""
        if not in_story:
            class_append += " hidden"
            x_pos, y_pos = None, None
        else:
            if not variable.story_position:
                print(f"no position set for {variable}")
                position = VariablePosition.objects.filter(variable=variable, story_id=DEFAULT_STORY_PK).first()
                if position is None:
                    print(f"default position had not yet been set for {variable}, setting to zero now")
                    position = VariablePosition(
                        variable=variable, story_id=DEFAULT_STORY_PK, x_pos=0.0, y_pos=0.0
                    )
                    position.save()
                x_pos, y_pos = position.x_pos, position.y_pos
            else:
                x_pos, y_pos = variable.story_position[0].x_pos, variable.story_position[0].y_pos

        cyto_elements.append(
            {"data": {"id": str(variable.pk),
                      "label": variable.label,
                      "sd_type": variable.sd_type,
                      "usable": usable,
                      "parent": parent,
                      "color": color,
                      "hierarchy": "variable"},
             "position": {"x": x_pos, "y": y_pos},
             "classes": "variable" + class_append}
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
                "source": str(connection.from_variable_id),
                "target": str(connection.to_variable_id),
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
                {"data": {"source": str(inflow.pk),
                          "target": str(stock.pk),
                          "has_equation": has_equation,
                          "edge_type": "Flow"},
                 "classes": "variable"}
            )
        for outflow in stock.outflows.all():
            has_equation = "no" if outflow.equation is None else "yes"
            cyto_elements.append(
                {"data": {"source": str(stock.pk),
                          "target": str(outflow.pk),
                          "has_equation": has_equation,
                          "edge_type": "Flow"},
                 "classes": "variable"}
            )

    # ELEMENTS
    # nodes
    elements = Element.objects.all().select_subclasses()
    for element in elements:
        if story_pk == DEFAULT_STORY_PK or element.pk in element_pks_in_story:
            in_story = True
        else:
            in_story = False

        class_append = "" if in_story else " hidden"

        cyto_elements.append(
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
                "classes": f"element {element.element_type}" + class_append
            }
        )

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
    element_groups = ElementGroup.objects.all().prefetch_related("elements")
    group_nodes = []
    for element_group in element_groups:
        element_pks = [obj.pk for obj in element_group.elements.all()]
        if story_pk == DEFAULT_STORY_PK or any(pk in element_pks_in_story for pk in element_pks):
            in_story = True
        else:
            in_story = False
        class_append = "" if in_story else " hidden"
        group_nodes.append({
            "data": {
                "id": f"group_{element_group.id}",
                "label": element_group.label,
                "hierarchy": "group"
            },
            "classes": "group" + class_append,
            "grabbable": False,
            "selectable": True,
            "pannable": True
        })
    cyto_elements.extend(group_nodes)

    # check that all connections have a valid source and target
    node_ids = [obj.get("data").get("id") for obj in cyto_elements if "id" in obj.get("data")]
    for obj in cyto_elements:
        if "source" in obj.get("data"):
            if obj.get("data").get("source") not in node_ids:
                raise ValueError(f"Source {obj.get('data').get('source')} not found in node ids")
            if obj.get("data").get("target") not in node_ids:
                raise ValueError(f"Target {obj.get('data').get('target')} not found in node ids")

    print(f"{current_story_pk=}")
    print(f"{story_pk=}")
    if current_story_pk == "init":
        return cyto_elements, story_pk, None
    else:
        return [{}], story_pk, json.dumps(cyto_elements)


@app.callback(
    Output("right-sidebar", "children"),
    Input("cyto", "selectedNodeData"),
    Input("cyto", "elements"),
)
@timer
def right_sidebar(selectednodedata, _):
    # INIT
    print(f"{selectednodedata=}")
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
        children.append(dbc.InputGroup(size="sm", children=[
            dbc.Select(
                id={"type": "add-connection-input", "index": "only-one"},
                options=[
                    {"label": upstream_element.label, "value": f"element_{upstream_element.pk}"}
                    for upstream_element in
                    Element.objects.exclude(downstream_connections__to_element=element).exclude(pk=element.pk)
                ],
            ),
            dbc.InputGroupAddon(addon_type="append", children=dbc.Button(
                id={"type": "add-connection-submit", "index": f"to-element_{element.pk}"}, children="Ajouter"
            ))
        ]))

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

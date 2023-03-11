import datetime

from django_plotly_dash import DjangoDash
from dash import html, dcc, ctx
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from sahel.models import *
from sahel.sd_model.model_operations import timer, run_model
import time
import pandas as pd
import plotly.graph_objects as go
from .mapping_styles import stylesheet, fieldvalue2color, partname2cytokey
from django.db.models import Prefetch, Q
import json
from .translations import l

# TODO: implement bulk edits for elements from interface

LITE = True
DEFAULT_SAMRAMODEL_PK = "1"
DEFAULT_ADM0 = "Mauritanie"
DEFAULT_STORY_PK = "1"
DEFAULT_LAYERS = [
    'group',
    # 'element',
    'variable',
]
LANG = "EN"
MALI_ADM1S = ["Gao", "Kidal", "Mopti", "Tombouctou", "Ménaka"]
MRT_ADM1S = ['Hodh Ech Chargi']

app = DjangoDash("mapping2modeling", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div(children=[
    # INIT
    # init div for populate initial values
    html.Div(id="init", hidden=True, children="init"),

    # OVERLAY
    # overlay stuff, all with position:absolute
    # (cannot click through divs in Dash for some reason, z-index not working either)
    html.Div(id="left-sidebar", className="mt-4 ml-4", style={"position": "absolute", "width": "200px"}, children=[
        # samramodel
        dbc.Select(id=(SAMRAMODEL_INPUT := "samramodel-input"), className=""),
        dbc.Select(id=(ADM0_INPUT := "adm0-input"), className="", bs_size="sm"),
        dbc.Select(id=(ADM1_INPUT := "adm1-input"), className="", bs_size="sm"),
        dbc.Select(id=(ADM2_INPUT := "adm2-input"), className="mb-3", bs_size="sm"),

        # layers
        dbc.Card(className="mb-3", children=[
            dbc.CardBody(className="p-2", children=[
                dbc.FormGroup(className="m-0", children=[
                    dbc.Label("Couches"),
                    dbc.Checklist(
                        id="layers-input",
                        options=[
                            {"label": f'{l("Group", LANG)}s', "value": "group"},
                            {"label": f'{l("Element", LANG)}s', "value": "element", "disabled": LITE},
                            {"label": f'{l("Variable", LANG)}s', "value": "variable"},
                        ],
                        value=DEFAULT_LAYERS,
                        switch=True,
                    )
                ])
            ])
        ]),

        # mapping / modeling tabs
        dbc.Tabs([
            dbc.Tab(label='Modeling', children=[
                dbc.Select(id=(SCENARIO_INPUT := "scenario-input"), placeholder="Scénario", className="mb-2"),
                dbc.Select(id=(RESPONSE_INPUT := "responseoption-input"), placeholder="Réponse", className="mb-2"),
                dbc.Button(
                    id=(RUN_SUBMIT := 'run-submit'), children="Exécuter modèle", className="mb-2", size='sm', color='primary',
                ),
            ]),
            dbc.Tab(label='Mapping', children=[
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

                dbc.Button(className="mb-3", id="add-eb-open", children="Add an EB", size="sm", color="primary"),
            ]),
        ]),
        # other
        dbc.Button(className="mb-3", id="download-submit", children="Télécharger SVG", size="sm", color="primary"),
        html.Br(),
        dbc.Button(className="mb-3", id="add-node-open", children="Ajouter un objet", size="sm", color="primary"),
        html.Br(),
        dbc.FormGroup([
            dbc.Checklist(id="allow-movement-switch",
                          options=[{"label": "Allow movement", "value": 1}],
                          value=[], switch=True, inline=True),
        ]),
        dbc.Button(className="mb-3", id="update-movement", children="GO", size="sm", color="primary"),
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
            dbc.InputGroup(id="add-node-sector-input-parent", className="mb-2", children=[
                dbc.InputGroupAddon("Sector", addon_type="prepend"),
                dbc.Select(id="add-node-sector-input"),
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

    # add EB
    dbc.Modal(id="add-eb-modal", is_open=False, children=[
        dbc.ModalHeader("Add an Evidence Bit"),
        dbc.ModalBody(children=[
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Source", addon_type="prepend"),
                dbc.Select(id="add-eb-source-input"),
            ]),
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Content", addon_type="prepend"),
                dbc.Textarea(id="add-eb-content-input"),
            ]),
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Label", addon_type="prepend"),
                dcc.DatePickerSingle(id="add-eb-date-input"),
            ]),
            dbc.InputGroup(className="mb-2", children=[
                dbc.InputGroupAddon("Elements", addon_type="prepend"),
                dcc.Dropdown(id="add-eb-elements-input", style={"width": "100%"}, multi=True),
            ]),
        ]),
        dbc.ModalFooter(className="d-flex justify-content-end", children=[
            dbc.Button(id="add-eb-close", className="ml-2", n_clicks=0, children="Cancel"),
            dbc.Button(id="add-eb-submit", className="ml-2", n_clicks=0, color="primary", children="Submit"),
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
            zoom=0.4,
            pan={"x": 500, "y": 300}
        ),
    ),

    # READOUTS
    html.P(id="current-story", hidden=True, children="init"),
    html.P(id=(RUN_READOUT := 'run-readout'), hidden=True),
    # store contains positions of elements BEFORE being moved around, and is None if not moving elements around
    dcc.Store(id="store"),
])


@app.callback(
    # color dropdowns
    *[[Output(f"color{part}-input", "options"), Output(f"color{part}-input", "value")]
      for part in ["body", "border"]],
    Output("samramodel-input", "options"),
    Output("samramodel-input", "value"),
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

    # samramodel
    samramodel_options = [
        {"value": model.get('id'), "label": model.get('name')}
        for model in SamraModel.objects.all().values()
    ]
    samramodel_value = DEFAULT_SAMRAMODEL_PK

    return color_options, color_value, color_options, color_value, samramodel_options, samramodel_value


@app.callback(
    Output("adm0-input", "options"),
    Output("adm0-input", "value"),
    Output("adm0-input", "disabled"),
    Output("scenario-input", "options"),
    Output("scenario-input", "value"),
    Output("scenario-input", "disabled"),
    Output("responseoption-input", "options"),
    Output("responseoption-input", "value"),
    Output("responseoption-input", "disabled"),
    Input("samramodel-input", "value")
)
def adm0_scenarioresponse_input(samramodel_pk):
    if samramodel_pk == "1":
        sahel_adm0s = [
            {'value': adm0, 'label': adm0}
            for adm0 in ADMIN0S
        ]
        scenario_options = [
            {'value': scenario.get('id'), 'label': scenario.get('name')}
            for scenario in Scenario.objects.filter(samramodel_id=samramodel_pk).values()
        ]
        scenario_value = scenario_options[0].get('value')
        response_options = [
            {'value': response.get('id'), 'label': response.get('name')}
            for response in ResponseOption.objects.filter(samramodel_id=samramodel_pk).values()
        ]
        response_value = '1'
        return (
            sahel_adm0s, DEFAULT_ADM0, False,
            scenario_options, scenario_value, False,
            response_options, response_value, False,
        )
    else:
        return None, None, True, \
               None, None, True, \
               None, None, True


@app.callback(
    Output("adm1-input", "options"),
    Output("adm1-input", "value"),
    Output("adm1-input", "disabled"),
    Input("adm0-input", "value")
)
def adm1_input(adm0_input):
    mali_adm1s = [
        {'value': adm1, 'label': adm1}
        for adm1 in MALI_ADM1S
    ]
    mrt_adm1s = [
        {'value': adm1, 'label': adm1}
        for adm1 in MRT_ADM1S
    ]
    if adm0_input == "Mali":
        return mali_adm1s, None, False
    elif adm0_input == "Mauritanie":
        return mrt_adm1s, 'Hodh Ech Chargi', False
    else:
        return None, None, True


@app.callback(
    Output("adm2-input", "options"),
    Output("adm2-input", "value"),
    Output("adm2-input", "disabled"),
    Input("adm1-input", "value")
)
def adm2_input(adm1_input):
    if adm1_input == "Hodh Ech Chargi":
        return [{'value': 'Bassikounou', 'label': 'Bassikounou'}], 'Bassikounou', False
    else:
        return None, None, True


@app.callback(
    Output("story-input", "options"),
    Output("story-input", "value"),
    Input("samramodel-input", "value")
)
def story_input(samramodel_pk):
    default_story_pk = SamraModel.objects.get(pk=samramodel_pk).default_story_id
    options = [{"value": default_story_pk, "label": "---"}]
    options.extend([
        {"value": story.pk, "label": story.name}
        for story in Story.objects.filter(samramodel_id=samramodel_pk, defaultfor__isnull=True)
    ])
    value = options[0].get("value")
    return options, value


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
            {"label": "Théorie de changement", "value": "theoryofchange"},
            {"label": "Shock structure", "value": "shockstructure"},
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
    elif subclass_input == "shockstructure":
        options = [
            {"label": sh_type[1], "value": sh_type[0]}
            for sh_type in ShockStructure.SHOCKSTRUCTURE_TYPES
        ]
        value = ShockStructure.SHOCK_EFFECT
        disabled = False
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
    Output("add-node-sector-input", "options"),
    Output("add-node-sector-input", "value"),
    Output("add-node-sector-input-parent", "hidden"),
    Input("samramodel-input", "value"),
    Input("add-node-class-input", "value")
)
def add_node_sector(samramodel_pk, class_input):
    if class_input == "element":
        sectors = Sector.objects.filter(samramodel_id=samramodel_pk)
        options = [{"value": "empty", "label": "---"}]
        options.extend([
            {"value": sector.pk, "label": sector.name}
            for sector in sectors
        ])
        value = "empty"
        return options, value, False
    else:
        return None, None, True


@app.callback(
    Output("add-eb-modal", "is_open"),
    Output("add-eb-source-input", "value"),
    Output("add-eb-elements-input", "value"),
    Output("add-eb-date-input", "date"),
    Output("add-eb-content-input", "value"),
    Output("add-eb-open", "n_clicks"),
    Output("add-eb-close", "n_clicks"),
    Output("add-eb-submit", "n_clicks"),
    # INPUTS
    Input("add-eb-open", "n_clicks"),
    Input("add-eb-close", "n_clicks"),
    Input("add-eb-submit", "n_clicks"),
    Input({"type": "select-eb", "index": ALL}, "n_clicks"),
    # STATES
    State("add-eb-source-input", "value"),
    State("add-eb-content-input", "value"),
    State("add-eb-date-input", "date"),
    State("add-eb-elements-input", "value"),
    State("add-eb-modal", "is_open"),
    State({"type": "select-eb", "index": ALL}, "id"),
)
def add_eb_modal(
        # INPUTS
        open_clicks, close_clicks, submit_clicks, eb_clicks,
        # STATES
        source_pk, content, date, elements, is_open, eb_ids
):
    if submit_clicks:
        eb = EvidenceBit(
                content=content,
                eb_date=date,
                source_id=source_pk,
            )
        eb.save()
        eb.elements.add(*[element for element in elements])
        return False, None, None, None, None, None, None, None
    if open_clicks or close_clicks:
        return not is_open, None, None, None, None, None, None, None
    for n_clicks, id in zip(eb_clicks, eb_ids):
        if n_clicks is not None:
            eb = EvidenceBit.objects.get(pk=id.get("index"))
            element_pks = [element.pk for element in eb.elements.all()]
            print(f"{eb.source_id=}")
            return True, eb.source_id, element_pks, eb.eb_date, eb.content, None, None, None
    raise PreventUpdate


@app.callback(
    Output("add-eb-elements-input", "options"),
    Output("add-eb-source-input", "options"),
    Input("samramodel-input", "value")
)
def add_eb_elements(samramodel_pk):
    element_options = [
        {"value": obj.get("id"), "label": obj.get("label")}
        for obj in Element.objects.filter(samramodel_id=samramodel_pk).values()
    ]
    source_options = [
        {"value": obj.get("id"), "label": obj.get("title")}
        for obj in Source.objects.filter(samramodels=samramodel_pk).values()
    ]
    print(f"{source_options}")
    return element_options, source_options


@app.callback(
    Output(RUN_READOUT, 'children'),
    Input(RUN_SUBMIT, 'n_clicks'),
    State(SAMRAMODEL_INPUT, 'value'),
    State(ADM0_INPUT, 'value'),
    State(SCENARIO_INPUT, 'value'),
    State(RESPONSE_INPUT, 'value'),
)
def run_model_from_dash(n_clicks, samramodel_pk, adm0, scenario_pk, response_pk):
    if n_clicks is None:
        raise PreventUpdate
    startdate = datetime.date(2023, 1, 1)
    enddate = datetime.date(2025, 1, 1)
    run_model([scenario_pk], [response_pk], samramodel_pk, adm0, startdate=startdate, enddate=enddate)
    return f"ran model for scenario {scenario_pk}, response {response_pk}, model {samramodel_pk}, admin0 {adm0}, " \
           f"startdate {startdate}, enddate {enddate}"


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
                 'width': '0',
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
    added_stylesheet.append({
        "selector": ".no_children",
        "style": {"text-valign": "center"}
    })

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
                        partname2cytokey.get(part_name): fieldvalue2color.get(part_field).get(choice[0]).get(part_name),
                        "background-blacken": -0.3,
                    }
                }
                for choice in SituationalAnalysis._meta.get_field(part_field).choices
            ])

    return stylesheet + added_stylesheet


@app.callback(
    Output("cyto", "autolock"),
    Input("allow-movement-switch", "value")
)
def lock_map(movement_allowed):
    if movement_allowed:
        return False
    else:
        return True


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
    # position lock switch
    Input("allow-movement-switch", "value"),
    # update movement button
    Input("update-movement", "n_clicks"),

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
    State("add-node-sector-input", "value"),
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
    # current SAMRA model
    State("samramodel-input", "value"),
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
        # change field - these need to match SA_FIELDS
        status_field_input, trend_field_input, resilience_field_input,
        # delete connection
        delete_connection_clicks,
        # add connection
        add_connection_clicks,
        # story
        story_pk,
        # element store
        cyto_elements_store,
        # position lock switch
        movement_allowed,
        # update movement button
        update_mvmt_clicks,

        # STATES
        # relationship modification
        select_ids, delete_ids, remove_ids, parentchild_ids, parentchild_input,
        # add node
        class_input, subclass_input, type_input, label_input, unit_input, sector_input, add_node_modal_is_open,
        # change fields - these need to match SA_FIELDS
        status_field_id, trend_field_id, resilience_field_id,
        # delete connection
        delete_connection_ids,
        # add connection
        add_connection_ids, add_connection_input,
        # story
        current_story_pk,
        # samra model
        samramodel_pk,
        # current elements read
        cyto_elements: list[dict],
):
    print("TOP OF REDRAW")
    print(f"{movement_allowed=}")
    print(f"{type(cyto_elements_store)=}")
    print(f"{update_mvmt_clicks=}")
    if cyto_elements is not None:
        print(f"{len(cyto_elements)=}")
    else:
        print(f"{cyto_elements=}")

    if movement_allowed:
        print(f"movement allowed")
        if cyto_elements_store is None:
            print(f"dumping into store")
            return [], current_story_pk, json.dumps(cyto_elements)
        else:
            print("store contains elements")
            if not cyto_elements:
                print("no elements in map, loading json")
                return json.loads(cyto_elements_store), current_story_pk, cyto_elements_store
            else:
                print("elements are in map, passing")
                pass
    else:
        print("movement not allowed")
        if current_story_pk != "init":
            print("story not init")
            moved_variables, moved_elements = [], []
            if cyto_elements_store is not None:
                print("movement not allowed, store contains elements, SAVING")
                old_positions = {
                    str(element.get("data").get("id")): element.get("position")
                    for element in json.loads(cyto_elements_store)
                    if "id" in element.get("data") and "position" in element
                }
                # TODO: bulk read old positions into dict instead of element by element
                for element in cyto_elements:
                    if "position" in element and "hidden" not in element.get("classes"):
                        id = element.get("data").get("id")
                        new_x, new_y = element.get('position').get("x"), element.get('position').get("y")
                        try:
                            old_x, old_y = old_positions.get(str(id)).get("x"), old_positions.get(str(id)).get("y")
                        except AttributeError:
                            old_x, old_y = None, None

                        if old_x != new_x or old_y != new_y:
                            if "variable" in element.get("classes"):
                                try:
                                    position = VariablePosition.objects.get(variable_id=id, story_id=story_pk)
                                    print(f"MOVED EXISTING {position}")
                                    position.x_pos, position.y_pos = new_x, new_y
                                    moved_variables.append(position)
                                except VariablePosition.DoesNotExist:
                                    print(f"ADDING NEW POSITIONS for {id}")
                                    VariablePosition(variable_id=id, story_id=story_pk, x_pos=new_x, y_pos=new_y).save()
                            elif "element" in element.get("classes"):
                                id = id.removeprefix("element_")
                                try:
                                    position = ElementPosition.objects.get(element_id=id, story_id=story_pk)
                                    print(f"MOVED EXISTING {position}")
                                    position.x_pos, position.y_pos = new_x, new_y
                                    moved_elements.append(position)
                                except ElementPosition.DoesNotExist:
                                    print(f"ADDING NEW POSITIONS for {id}")
                                    ElementPosition(element_id=id, story_id=story_pk, x_pos=new_x, y_pos=new_y).save()
                VariablePosition.objects.bulk_update(moved_variables, ["x_pos", "y_pos"])
                ElementPosition.objects.bulk_update(moved_elements, ["x_pos", "y_pos"])
                return cyto_elements, current_story_pk, None
            else:
                print("store is empty, passing")
                pass

    # SELECT NODE
    for n_clicks, id in zip(select_clicks, select_ids):
        if n_clicks is not None:
            selected_id = id.get("index")
            print(f"clicked on {selected_id}")
            display_element = {}
            for element in cyto_elements:
                if element.get("data").get("id") == selected_id:
                    element.update({"selected": True})
                    display_element = element
                else:
                    element.update({"selected": False})
            return cyto_elements, current_story_pk, None

    # DELETE NODE
    # there is a Dash Cytoscape bug where the child nodes also get removed when the parent is removed
    # there is also a problem that the node remains selected after being deleted, so callback doesn't run
    for n_clicks, id in zip(delete_clicks, delete_ids):
        if n_clicks is not None:
            deleted_id = id.get("index")
            if "element" in deleted_id:
                Element.objects.get(pk=deleted_id.removeprefix("element_")).delete()
            elif "group" in deleted_id:
                ElementGroup.objects.get(pk=deleted_id.removeprefix("group_")).delete()
            updated_cyto_elements = []
            for element in cyto_elements:
                if element.get("data").get("parent") == deleted_id:
                    element.get("data").update({"parent": None})
                if element.get("data").get("id") != deleted_id:
                    updated_cyto_elements.append(element)
            return cyto_elements, current_story_pk, None

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
            for element in cyto_elements:
                if element.get("data").get("id") == child_id.removeprefix("variable_"):
                    element.get("data").update({"parent": None})
                    display_element = element
            return cyto_elements, current_story_pk, None

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
                for element in cyto_elements:
                    if element.get("data").get("id") == child_id.removeprefix("variable_"):
                        element.get("data").update({"parent": f"{parent_class_str}_{parentchild_input[0]}"})
            return cyto_elements, current_story_pk, None

    # ADD NODE
    if add_node_clicks > 0 and add_node_modal_is_open:
        print(f"{samramodel_pk=}")
        if class_input == "group":
            element_group = ElementGroup(label=label_input, samramodel_id=samramodel_pk)
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
            return cyto_elements, current_story_pk, None
        elif class_input == "element":
            element = None
            if subclass_input == "situationalanalysis":
                element = SituationalAnalysis(label=label_input, element_type=type_input, samramodel_id=samramodel_pk)
            elif subclass_input == "theoryofchange":
                element = TheoryOfChange(label=label_input, element_type=type_input, samramodel_id=samramodel_pk)
            elif subclass_input == "shockstructure":
                element = ShockStructure(label=label_input, element_type=type_input, samramodel_id=samramodel_pk)
            element.save()
            if sector_input is not None and sector_input != "empty":
                element.sectors.add(sector_input)
            ElementPosition(element=element, story_id=story_pk, x_pos=0.0, y_pos=0.0).save()
            cyto_elements.append(
                {"data": {"id": f"element_{element.pk}",
                          "label": element.label,
                          "hierarchy": "element",
                          "parent": f"group_{element.element_group_id}"},
                 "classes": f"element no_children {element.element_type}",
                 "position": {"x": 0.0, "y": 0.0}}
            )
            return cyto_elements, current_story_pk, None
        elif class_input == "variable":
            variable = Variable(label=label_input, sd_type=type_input, unit=unit_input, samramodel_id=samramodel_pk)
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
            return cyto_elements, current_story_pk, None

    # CHANGE FIELD
    if status_field_input:
        for field in SituationalAnalysis.SA_FIELDS:
            # these need to match SA_FIELDS
            if field == "status":
                value, id = status_field_input, status_field_id
            elif field == "trend":
                value, id = trend_field_input, trend_field_id
            elif field == "resilience_vulnerability":
                value, id = resilience_field_input, resilience_field_id
            else:
                value, id = None, None

            value = value[0]
            id = id[0]

            element = SituationalAnalysis.objects.get(pk=id.get("index").removeprefix("element_"))
            old_value = getattr(element, field)

            if value != old_value:
                setattr(element, field, value)
                element.save()
                print(f"SAVED ELEMENT {element} with {field=}, {value=}")
                for cyto_element in cyto_elements:
                    if cyto_element.get("data").get("id") == id.get("index"):
                        print("FOUND IT")
                        print(f"{cyto_element=}")
                        print(f"{field=}, {value=}")
                        cyto_element.get("data").update({field: value})
                return cyto_elements, current_story_pk, None

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
            return cyto_elements, current_story_pk, None

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
            return cyto_elements, current_story_pk, None

    if current_story_pk == story_pk:
        raise PreventUpdate

    ## CHANGE VIEW
    # init
    print("redrawing whole model")

    cyto_elements = []
    # get elements_pks in story
    default_story_pk = SamraModel.objects.get(pk=samramodel_pk).default_story_id
    story_pk = int(story_pk)
    print(f"{default_story_pk=}")
    print(f"{story_pk=}")
    if story_pk == default_story_pk:
        elements = Element.objects.filter(samramodel_id=samramodel_pk)
    else:
        elements = Element.objects.filter(stories=story_pk)

    print(f"{len(elements)=}")
    element_pks_in_story = [element.pk for element in elements]

    # VARIABLES
    # nodes
    queryset = VariablePosition.objects.filter(story_id=story_pk)
    variables = Variable.objects.filter(
        Q(element_id__in=element_pks_in_story) |
        Q(samramodel_id=samramodel_pk)
    ).prefetch_related(Prefetch(
        "variablepositions", queryset=queryset, to_attr="story_position"
    ))
    print(f"{len(variables)=}")
    variable_pks = [variable.pk for variable in variables]
    for variable in variables:
        color = "white"
        usable = True
        if variable.sd_type in ["Variable", "Flow"] and variable.equation is None:
            usable = False

        parent = None
        if not LITE and variable.element_id is not None:
            parent = f"element_{variable.element_id}"
        elif variable.element_group_id is not None:
            parent = f"group_{variable.element_group_id}"

        # TODO: implement in_story functionality
        if story_pk == DEFAULT_STORY_PK or variable.element_id in element_pks_in_story:
            in_story = True
        else:
            in_story = False

        in_story = True

        class_append = ""
        if not in_story:
            class_append += " hidden"
            x_pos, y_pos = None, None
        else:
            if not variable.story_position:
                print(f"no position set for {variable}")
                position = VariablePosition.objects.filter(variable=variable, story_id=default_story_pk).first()
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
             "classes": "variable"}
        )

    # connections
    connections = VariableConnection.objects.filter(
        to_variable_id__in=variable_pks, from_variable_id__in=variable_pks
    ).select_related("to_variable")
    print(f"{len(connections)=}")
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
    stocks = Variable.objects.filter(sd_type="Stock", pk__in=variable_pks).prefetch_related("inflows", "outflows")
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

    # TODO: find way to implement this quicker when not using elements

    if not LITE:
        # nodes
        queryset = ElementPosition.objects.filter(story_id=story_pk)
        elements = elements.select_subclasses().prefetch_related(
            Prefetch("elementpositions", queryset=queryset, to_attr="story_position"),
            Prefetch("variables")
        )
        print(f"{len(elements)=}")
        for element in elements:
            if element.pk in element_pks_in_story:
                in_story = True
            else:
                in_story = False

            class_append = "" if in_story else " hidden"
            if not element.variables.exists():
                class_append += " no_children"
                if not element.story_position:
                    print(f"no position set for {element}")
                    position = ElementPosition.objects.filter(element=element, story_id=default_story_pk).first()
                    if position is None:
                        print(f"default position had not yet been set for {element}, setting to zero now")
                        position = ElementPosition(
                            element=element, story_id=default_story_pk, x_pos=0.0, y_pos=0.0
                        )
                        position.save()
                    x_pos, y_pos = position.x_pos, position.y_pos
                else:
                    x_pos, y_pos = element.story_position[0].x_pos, element.story_position[0].y_pos
            else:
                x_pos, y_pos = None, None

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
                    "classes": f"element {element.element_type}" + class_append,
                    "position": {"x": x_pos, "y": y_pos}
                }
            )

        # connections
        elementconnections = ElementConnection.objects.filter(
            to_element_id__in=element_pks_in_story, from_element_id__in=element_pks_in_story
        ).select_related(
            "from_element__situationalanalysis", "from_element__theoryofchange", "from_element__shockstructure"
        )
        print(f"{len(elementconnections)=}")
        for connection in elementconnections:
            element_type = ""
            try:
                element_type += " " + connection.from_element.theoryofchange.element_type
            except Element.theoryofchange.RelatedObjectDoesNotExist:
                pass
            try:
                element_type += " " + connection.from_element.situationalanalysis.element_type
            except Element.situationalanalysis.RelatedObjectDoesNotExist:
                pass
            try:
                element_type += " " + connection.from_element.shockstructure.element_type
            except Element.shockstructure.RelatedObjectDoesNotExist:
                pass
            cyto_elements.append({
                "data": {
                    "source": f"element_{connection.from_element_id}",
                    "target": f"element_{connection.to_element_id}"
                },
                "classes": "element" + element_type
            })

    # GROUPS
    element_groups = ElementGroup.objects.all().prefetch_related("elements")
    group_nodes = []
    for element_group in element_groups:
        element_pks = [obj.pk for obj in element_group.elements.all()]
        if story_pk == default_story_pk or any(pk in element_pks_in_story for pk in element_pks):
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

    if current_story_pk == "init":
        print("story is init, drawing elements, making store None")
        return cyto_elements, story_pk, None
    else:
        print("story is not init")
        if movement_allowed:
            print("movement is allowed, dumping into store")
            return [], story_pk, json.dumps(cyto_elements)
        else:
            print("movement is not allowed, drawing elements, making store None")
            return cyto_elements, story_pk, None



@app.callback(
    Output("right-sidebar", "children"),
    Input("cyto", "selectedNodeData"),
    Input("cyto", "elements"),
    Input("adm0-input", "value"),
    Input('scenario-input', 'value'),
    Input('responseoption-input', 'value'),
    State("allow-movement-switch", "value"),
    State("samramodel-input", "value")
)
@timer
def right_sidebar(selectednodedata, cyto_elements, adm0, scenario_pk, responseoption_pk, movement_allowed, samrammodel_pk):
    # TODO: admin1 and admin2 filtering on graph
    # TODO: prefetch everything relevant to speed up
    # TODO: add other constant types
    # INIT
    children = []
    if not selectednodedata or movement_allowed:
        return children
    nodedata = selectednodedata[-1]
    admin1 = None
    variables = [cyto_element for cyto_element in cyto_elements if 'position' in cyto_element]

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
        pk = nodedata.get("id").removeprefix("element_")
        start = time.time()
        # fetch element and all related information
        element = Element.objects.prefetch_related(
            "variables", "upstream_connections__from_element", "evidencebits"
        ).select_related(
            "element_group"
        ).get_subclass(pk=pk)
        print(f"TIME: {round(time.time() - start, 2)} for element fetch")
        start = time.time()

        # label and type
        element_text = "ÉLÉMENT" if LANG == "FR" else "ELEMENT"
        children.append(html.H4(className="mb-2 h4", children=element.label))
        children.append(html.H6(className="mb-3 font-italic text-secondary font-weight-light h6",
                                children=f"{element_text} | {element.__class__._meta.verbose_name} | "
                                         f"{element.get_element_type_display()}"))
        print(f"TIME: {round(time.time() - start, 2)} for element label and type")
        start = time.time()

        # description
        children.append(html.P(className="mb-0 font-weight-bold", children="Description"))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        children.append(html.P(
            style={"max-height": "100px", "overflow-y": "scroll", "font-size": "small"},
            children=element.description
        ))

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
                                 for elementgroup in ElementGroup.objects.filter(samramodel_id=samrammodel_pk)],
                    ),
                    dbc.InputGroupAddon(addon_type="append", children=dbc.Button(
                        id={"type": "parentchild-submit", "index": f"child-element_{element.pk}"}, children="Saisir"
                    ))
                ]),
            ])
        )
        print(f"TIME: {round(time.time() - start, 2)} for element parent")
        start = time.time()

        # children
        children.append(html.P(className="mb-0 font-weight-bold", children=f"Variables / {l('Indicator', LANG)}s"))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        children.extend([
            dbc.Button(
                id={"type": "select-node", "index": str(variable.pk)},
                className="mb-1 mr-1", outline=True, color="secondary", size="sm", children=variable.label
            )
            for variable in element.variables.all()
        ])
        print(f"TIME: {round(time.time() - start, 2)} for element children")
        start = time.time()

        # upstream
        children.append(html.P(className="mb-0 font-weight-bold", children=l("Upstream Element", LANG) + "s"))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        children.append(html.Div(style={"max-height": "100px", "overflow-x": "scroll"}, children=[
            dbc.ButtonGroup(className="mb-1 mr-1", size="sm", children=[
                dbc.Button(
                    id={"type": "select-node", "index": f"element_{upstream_connection.from_element.pk}"},
                    outline=True, color="secondary", children=upstream_connection.from_element.label
                ),
                dbc.Button(
                    id={"type": "delete-connection",
                        "index": f"element_{upstream_connection.from_element.pk}-to-element_{element.pk}"},
                    outline=True, color="danger", children="x"
                )
            ])
            for upstream_connection in element.upstream_connections.all()
        ]))
        print(f"TIME: {round(time.time() - start, 2)} for element upstream existing")
        start = time.time()
        children.append(dbc.InputGroup(size="sm", children=[
            dbc.Select(
                id={"type": "add-connection-input", "index": "only-one"},
                options=[
                    {"label": upstream_element.get("label"), "value": f"element_{upstream_element.get('pk')}"}
                    for upstream_element in
                    Element.objects.filter(samramodel_id=samrammodel_pk)
                        .exclude(downstream_connections__to_element=element).exclude(pk=element.pk).values()
                ],
            ),
            dbc.InputGroupAddon(addon_type="append", children=dbc.Button(
                id={"type": "add-connection-submit", "index": f"to-element_{element.pk}"}, children="Ajouter"
            ))
        ]))
        print(f"TIME: {round(time.time() - start, 2)} for element upstream add")
        start = time.time()

        # status, trend, resilience for SA only
        if isinstance(element, SituationalAnalysis):
            children.append(html.P(className="mt-3 mb-0 font-weight-bold", children="Characteristics"))
            children.append(html.Hr(className="mb-2 mt-1 mx-0"))
            children.extend([
                dbc.InputGroup(className="mb-2", size="sm", children=[
                    dbc.InputGroupAddon(addon_type="prepend", children=field.capitalize()),
                    dbc.Select(
                        id={"type": f"{field}-input", "index": f"element_{element.pk}"},
                        options=[
                            {"value": choice[0], "label": choice[1]}
                            for choice in SituationalAnalysis._meta.get_field(field).choices
                        ],
                        value=getattr(element, field)
                    )
                ])
                for field in SituationalAnalysis.SA_FIELDS
            ])

            children.append(html.P(className="mt-3 mb-0 font-weight-bold", children="Fields"))
            children.append(html.Hr(className="mb-2 mt-1 mx-0"))
            children.extend([
                dbc.InputGroup(className="mb-2", size="sm", children=[
                    dbc.InputGroupAddon(addon_type="prepend", children=field.name),
                    dbc.Select(
                        id={"type": f"{field.pk}-input", "index": f"element_{element.pk}"},
                        options=[
                            {"value": option.pk, "label": option.label}
                            for option in SAFieldOption.objects.filter(safield=field)
                        ],
                        value=SAFieldValue.objects.get(sa=element, safieldoption__safield=field).pk if
                        SAFieldValue.objects.filter(sa=element, safieldoption__safield=field).exists() else None
                    )
                ])
                for field in SAField.objects.all()
            ])
        print(f"TIME: {round(time.time() - start, 2)} for element status etc")
        start = time.time()


        # EBs
        children.append(html.P(className="mt-4 mb-0 font-weight-bold", children=l("Evidence Bit", LANG)))
        children.append(html.Hr(className="mb-2 mt-1 mx-0"))
        for eb in element.evidencebits.all():
            truncate_length = 10
            content = eb.content if len(eb.content) < truncate_length else eb.content[:truncate_length] + "..."
            children.append(
                dbc.ButtonGroup(className="mb-1 mr-1", size="sm", children=[
                    dbc.Button(
                        id={"type": "select-eb", "index": eb.pk},
                        outline=True, color="secondary", children=content
                    ),
                    dbc.Button(
                        id={"type": "remove-eb", "index": eb.pk},
                        outline=True, color="danger", children="x"
                    )
                ])
            )
        print(f"TIME: {round(time.time() - start, 2)} for element EBs")
        start = time.time()

        # delete
        children.append(html.Hr(className="mb-2 mt-4 mx-0"))
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
        if not LITE:
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
        if variable.sd_type in [Variable.STOCK, Variable.FLOW, Variable.VARIABLE, Variable.INPUT]:
            fig = go.Figure(layout=go.Layout(template="simple_white", margin=go.layout.Margin(l=0, r=0, b=0, t=0)))
            fig.update_xaxes(title_text="Date")

            # simulated DPs
            # TODO: disagg by admin1-2
            df = pd.DataFrame(SimulatedDataPoint.objects
                              .filter(element=variable, scenario_id=scenario_pk, responseoption_id=responseoption_pk, admin0=adm0)
                              .values("date", "value"))
            if not df.empty:
                fig.add_trace(go.Scatter(
                    x=df["date"],
                    y=df["value"],
                    name="Simulé",
                ))

            # measured DPs
            # TODO: disagg by admin2
            mdps = MeasuredDataPoint.objects.filter(element=variable, admin0=adm0)
            if admin1 is not None:
                mdps = mdps.filter(admin1=admin1)
            df = pd.DataFrame(mdps.values())

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
                yaxis=dict(title=variable.unit.replace("LCY", CURRENCY.get(adm0)) + unit_append),
            )
            fig_div = dcc.Graph(figure=fig, id="element-detail-graph", style={"height": "300px"}, className="mb-2")
            children.append(fig_div)

        # TODO: show seasonal values
        if variable.sd_type in ["Flow", "Variable"]:
            # connections
            if not LITE:
                # upstream
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

                # downstream
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
                for eq_variable in variables:
                    equation_text = equation_text.replace(
                        f"_E{eq_variable.get('data').get('id')}_",
                        eq_variable.get('data').get('label')
                    )
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
            if not LITE:
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

                # outflows
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
                value = variable.householdconstantvalues.get(admin0=adm0).value
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

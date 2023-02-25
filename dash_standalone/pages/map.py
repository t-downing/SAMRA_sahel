import dash
from dash import html, dcc, callback, Input, Output
import requests
import dash_bootstrap_components as dbc
from dash_standalone.utils import sidebar
import dash_cytoscape as cyto
# from sahel.sd_model.mapping_styles import stylesheet

PAGE_NAME = 'Map'

dash.register_page(__name__, name=PAGE_NAME)

layout = html.Div(children=[
    html.Div(id='init', hidden=True),
    html.Div(id=f'{PAGE_NAME}-sidebar'),
    html.Div(
        id="left-sidebar",
        className="mt-4 ml-4",
        style={"position": "fixed", "width": "200px", 'top': 0, 'left': 200, 'zIndex': 1},
        children=[
            dbc.Card(className='mb-3', children=[
                dbc.CardBody(className='p-2', children=[
                    'HELLO'
                ])
            ])
        ]
    ),
    html.Div(
        style={
            "position": "fixed",
            "top": 0,
            'left': 200,
            "width": "100%",
            "zIndex": "0",
        },
        children=cyto.Cytoscape(
            id="cyto",
            # layout={"name": "preset", "fit": False},
            style={"height": "100vh", "background-color": "#f8f9fc"},
            # stylesheet=stylesheet,
            # minZoom=0.2,
            # maxZoom=2.0,
            # boxSelectionEnabled=True,
            autoRefreshLayout=True,
            # responsive=True,
            # zoom=0.4,
            # pan={"x": 500, "y": 300},
        ),
    ),
])


@callback(
    Output(f'{PAGE_NAME}-sidebar', 'children'),
    Output(f'{PAGE_NAME}-sidebar', 'style'),
    Input('init', 'children')
)
def nav(_):
    return sidebar(PAGE_NAME)


@callback(
    Output('cyto', 'elements'),
    Input('init', 'children')
)
def draw_map(_):
    dummy_elements = [
        {
            "data": {
                "id": '1',
                "label": 'HELLO',
            },
            "position": {"x": 0.0, "y": 0.0},
        },
    ]
    return dummy_elements


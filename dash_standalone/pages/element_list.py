import dash
from dash import html, dcc, callback, Input, Output
import requests
import dash_bootstrap_components as dbc
from dash_standalone.utils import sidebar

PAGE_NAME = 'Element List'

dash.register_page(__name__, name=PAGE_NAME)

layout = dbc.Row(className='vh-100', children=[
    html.Div(id='init'),
    dbc.Col(id=f'{PAGE_NAME}-sidebar'),
    dbc.Col(className='h-100 overflow-scroll', children=[
        html.Div(id='elements-list')
    ])
])


@callback(
    Output(f'{PAGE_NAME}-sidebar', 'children'),
    Output(f'{PAGE_NAME}-sidebar', 'width'),
    Output(f'{PAGE_NAME}-sidebar', 'style'),
    Input('init', 'children')
)
def nav(_):
    return sidebar(PAGE_NAME)


@callback(
    Output('elements-list', 'children'),
    Input('init', 'children'),
)
def elements_list(_):
    api_url = 'http://127.0.0.1:8000/api/elements'
    response = requests.get(api_url)
    element_labels = [obj.get('label') for obj in response.json()]
    return element_labels

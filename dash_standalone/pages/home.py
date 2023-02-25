import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from dash_standalone.utils import sidebar

PAGE_NAME = 'Home'

dash.register_page(__name__, name=PAGE_NAME, path='/')

layout = dbc.Row(className='vh-100', children=[
    html.Div(id='init'),
    dbc.Col(id=f'{PAGE_NAME}-sidebar'),
    dbc.Col(children=[
        'HELLO'
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
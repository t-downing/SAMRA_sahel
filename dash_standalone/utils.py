import dash_bootstrap_components as dbc
import dash
from dash import html


def sidebar(active_title):
    children = [
        html.Img(className='p-3 w-100', src='assets/SAMRA_logo.png'),
        dbc.Nav(vertical=True, pills=True, children=[
            dbc.NavItem(dbc.NavLink(
                page['name'],
                href=page['path'],
                active=True if active_title == page['name'] else False
            ))
            for page in dash.page_registry.values()
        ]),
    ]
    style = {
        'background-color': '#368365',
        'height': '100vh',
        'width': '200px',
        'overflow': 'scroll',
        'position': 'fixed',
    }
    return children, style
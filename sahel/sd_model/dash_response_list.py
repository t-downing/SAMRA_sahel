import time

from django_plotly_dash import DjangoDash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Element, Scenario, MeasuredDataPoint
from sahel.sd_model.model_operations import run_model

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
import itertools
import pandas as pd

tooltip_style = {"text-decoration-line": "underline", "text-decoration-style": "dotted"}

app = DjangoDash("responselist", external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(fluid=True, style={"background-color": "#f8f9fc"}, children=[
    dbc.Row([
        dbc.Col([
            html.H4(id="title", className="mb-4", children="Liste de réponses"),
        ]),
    ]),
    dbc.Row([
        dbc.Col(width=12, children=[
            dash_table.DataTable(
                id="table",
                style_cell={
                    'textAlign': 'left', 'font-family': 'sans-serif',
                    'minWidth': '50px', 'width': '50px', 'maxWidth': '50px',
                    'height': 'auto', 'whiteSpace': 'pre-line'
                },
                style_table={'overflowX': 'auto'},
                merge_duplicate_headers=True,

            ),
        ]),
    ]),
])


@app.callback(
    Output("table", "data"),
    Output("table", "columns"),
    Input("title", "children"),
)
def populate_initial(_):
    responseoptions = ResponseOption.objects.all().values().exclude(pk=1)
    data = [{"name": responseoption.get("name")} for responseoption in responseoptions]
    columns = [{"name": ["", "Réponse"], "id": "name"},
               {"name": ["", "Coûts totaux\n(FCFA)"], "id": "cost"},
               {"name": ["Revenu total", "+/- abs.\n(FCFA)"], "id": "revenue_abs"},
               {"name": ["Revenu total", "+/- par coût\n(FCFA / FCFA)"], "id": "revenue_cost"},
               {"name": ["Stock final", "+/- abs.\n(tête)"], "id": "stock_abs"},
               {"name": ["Stock final", "+/- par coût\n(tête / FCFA)"], "id": "stock_cost"},
               {"name": ["Actifs final", "+/- abs.\n(FCFA)"], "id": "assets_abs"},
               {"name": ["Actifs final", "+/- par coût\n(FCFA / FCFA)"], "id": "assets_cost"},
               {"name": ["Consommation moyen", "+/- abs.\n(%)"], "id": "frac_abs"},
               {"name": ["Consommation moyen", "+/- par coût\n(% / FCFA)"], "id": "frac_cost"}]
    element_pks = [194, 77, 203, 104]
    df = pd.DataFrame(SimulatedDataPoint.objects.filter(element_id__in=element_pks).values())
    print(df)
    for pk in element_pks:
        pass
    return data, columns


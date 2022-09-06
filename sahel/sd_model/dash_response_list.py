import time

from django_plotly_dash import DjangoDash
from dash import html, dcc, dash_table
from dash.dash_table.Format import Format, Scheme, Sign
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Element, Scenario, MeasuredDataPoint
from sahel.sd_model.model_operations import run_model, read_results

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
import itertools
import pandas as pd
import numpy as np
import colorlover

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
            dcc.Loading(dash_table.DataTable(
                id="table",
                style_cell={
                    'font-family': 'sans-serif',
                    'minWidth': '50px', 'width': '50px', 'maxWidth': '50px',
                    'height': 'auto', 'whiteSpace': 'pre-line',
                },
                style_header={'textAlign': 'center', 'fontWeight': 'bold'},
                sort_action="native",
                style_table={'overflowX': 'auto'},
                merge_duplicate_headers=True,
                style_as_list_view=True,
            )),
        ]),
    ]),
])


@app.callback(
    Output("table", "data"),
    Output("table", "columns"),
    Output("table", "style_data_conditional"),
    Input("title", "children"),
)
def populate_initial(_):
    responseoptions = ResponseOption.objects.all().values()

    columns = [{
        "id": "responseoption__name",
        "name": ["", "Réponse"],
        "type": "text"
    }]
    cost_element_pk = 102
    element_pks = [194, 77, 203, 140]
    scenario_pks = [3]
    response_pks = [responseoption.get("id") for responseoption in responseoptions]
    results = pd.DataFrame()

    # read cost value
    df, df_cost, df_agg, df_cost_agg, agg_text, agg_unit, divider_text = read_results(
        element_pk=cost_element_pk, scenario_pks=scenario_pks, response_pks=response_pks,
    )
    columns.append({
        "id": "total_cost",
        "name": ["", "Coûts totaux\n(FCFA)"],
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.decimal)
    })
    df_agg = df_agg.rename(columns={"value": "total_cost"}).set_index("responseoption__name")
    results = pd.concat([results, df_agg["total_cost"]], axis=1)

    # read all element values
    for element_pk in element_pks:
        element = Element.objects.get(pk=element_pk)
        df, df_cost, df_agg, df_cost_agg, agg_text, agg_unit, divider_text = read_results(
            element_pk=element_pk, scenario_pks=scenario_pks, response_pks=response_pks,
        )

        eff_unit = "1" if agg_unit == "1000 FCFA" else f"{agg_unit} / {divider_text} FCFA"
        columns.extend([
            {"id": f"{element_pk}_abs",
             "name": [f"{element.label}, {agg_text}", f"Abs.\n({agg_unit})"],
             "type": 'numeric',
             "format": Format(precision=2, scheme=Scheme.decimal)},
            {"id": f"{element_pk}_change",
             "name": [f"{element.label}, {agg_text}", f"+/-\n({agg_unit})"],
             "type": 'numeric',
             "format": Format(precision=2, scheme=Scheme.decimal, sign=Sign.positive)},
            {"id": f"{element_pk}_costeff",
             "name": [f"{element.label}, {agg_text}", f"+/- par coût\n({eff_unit})"],
             "type": 'numeric',
             "format": Format(precision=2, scheme=Scheme.decimal, sign=Sign.positive)},
        ])
        df_agg = df_agg[["responseoption__name", "value", "baseline_diff", "cost_eff"]]
        df_agg = df_agg.rename(columns={"value": f"{element_pk}_abs",
                                        "baseline_diff": f"{element_pk}_change",
                                        "cost_eff": f"{element_pk}_costeff"})
        df_agg = df_agg.set_index("responseoption__name")
        results = pd.concat([results, df_agg], axis=1)
    results = results.reset_index().rename(columns={"index": "responseoption__name"})
    results = results.replace([np.inf, -np.inf], np.nan)
    data = results.to_dict("records")

    style_cell_conditional = [
        {"if": {"column_id": "responseoption__name"},
         "textAlign": "left"}
    ]

    heat_map_styles = discrete_background_color_bins(results)
    style_cell_conditional.extend(heat_map_styles)

    return data, columns, style_cell_conditional


def discrete_background_color_bins(df, n_bins=7, columns='all'):
    bounds = [i * (1.0 / n_bins) for i in range(n_bins + 1)]
    if columns == 'all':
        if 'id' in df:
            df_numeric_columns = df.select_dtypes('number').drop(['id'], axis=1)
        else:
            df_numeric_columns = df.select_dtypes('number')
    else:
        df_numeric_columns = df[columns]

    styles = []
    for column in df_numeric_columns:
        df_max = df_numeric_columns[column].max().max()
        df_min = df_numeric_columns[column].min().min()
        print(df_max)
        print(df_min)
        ranges = [
            ((df_max - df_min) * i) + df_min
            for i in bounds
        ]
        for i in range(1, len(bounds)):
            min_bound = ranges[i - 1]
            max_bound = ranges[i]
            backgroundColor = colorlover.scales[str(n_bins)]['seq']['Blues'][i - 1]
            color = 'white' if i > len(bounds) / 2. else 'inherit'

            styles.append({
                'if': {
                    'filter_query': (
                        '{{{column}}} >= {min_bound}' +
                        (' && {{{column}}} < {max_bound}' if (i < len(bounds) - 1) else '')
                    ).format(column=column, min_bound=min_bound, max_bound=max_bound),
                    'column_id': column
                },
                'backgroundColor': backgroundColor,
                'color': color
            })

    return styles

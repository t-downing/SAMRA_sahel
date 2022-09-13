import time

from django_plotly_dash import DjangoDash
from dash import html, dcc, dash_table
from dash.dash_table.Format import Format, Scheme, Sign
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Variable, Scenario, MeasuredDataPoint
from sahel.sd_model.model_operations import run_model, read_results

import plotly.graph_objects as go
from plotly.colors import DEFAULT_PLOTLY_COLORS
import itertools
import pandas as pd
import numpy as np
import colorlover

tooltip_style = {"text-decoration-line": "underline", "text-decoration-style": "dotted"}

app = DjangoDash("responselist", external_stylesheets=[dbc.themes.BOOTSTRAP])

page_description = """
Ci-dessous est une liste des réponses qu'on a investigué avec le modèle. Pour chaque réponse, on peut voir comment la
réponse influence certains éléments clés du modèle. Passer le curseur les différentes colonnes pour informer ce qu'elles
indiquent.
"""

app.layout = dbc.Container(fluid=True, style={"background-color": "#f8f9fc"}, children=[
    dbc.Row([
        dbc.Col([
            html.P(id="init", className="mb-4", children=page_description)
        ]),
    ]),
    dbc.Row([
        dbc.Col(width=12, children=[
            dbc.Card(className="shadow mb-4", children=[
                dbc.CardBody(
                    dcc.Loading(dash_table.DataTable(
                        id="table",
                        style_cell={
                            'font-family': 'sans-serif',
                            'minWidth': '50px', 'width': '50px', 'maxWidth': '50px',
                            'height': 'auto', 'whiteSpace': 'pre-line',
                        },
                        style_header={'textAlign': 'center', 'fontWeight': 'bold', **tooltip_style},
                        style_header_conditional=[
                            {"if": {"header_index": 1},
                             "fontWeight": ""},
                            {"if": {"column_id": ["responseoption__name", "total_cost"]},
                             "fontWeight": "bold"}
                        ],
                        style_data_conditional=[
                            {"if": {"column_id": "responseoption__name"},
                             "textAlign": "left", 'fontStyle': 'italic', **tooltip_style}
                        ],
                        sort_action="native",
                        style_table={'overflowX': 'auto'},
                        merge_duplicate_headers=True,
                        style_as_list_view=True,
                        tooltip_delay=0,
                        tooltip_duration=None,
                        css=[
                            {'selector': '.dash-table-tooltip',
                             'rule': 'background-color: black; color: white; font-size: small'}
                        ],
                    )),
                )
            ])
        ]),
    ]),
])


@app.callback(
    Output("table", "data"),
    Output("table", "columns"),
    Output("table", "tooltip_header"),
    Output("table", "tooltip_data"),
    Output("table", "style_data_conditional"),
    Input("init", "children"),
    State("table", "style_data_conditional"),
)
def populate_initial(_, style_data_conditional):
    responseoptions = ResponseOption.objects.all().values()

    columns = [{
        "id": "responseoption__name",
        "name": ["", "Réponse"],
        "type": "text"
    }]
    tooltip_header = {
        "responseoption__name": ["", """
        La collection des interventions que le CICR fait pour supporter les populations cibles.
        """]
    }
    cost_element_pk = 102
    element_pks = [194, 77, 203, 140]
    scenario_pks = [3]
    response_pks = [responseoption.get("id") for responseoption in responseoptions]
    results = pd.DataFrame()

    # read cost value
    element = Variable.objects.get(pk=cost_element_pk)
    df, df_cost, df_agg, df_cost_agg, agg_text, agg_unit, divider_text = read_results(
        element_pk=cost_element_pk, scenario_pks=scenario_pks, response_pks=response_pks,
    )
    columns.append({
        "id": "total_cost",
        "name": ["", "Coûts totaux\n(1000 FCFA)"],
        "type": "numeric",
        "format": Format(precision=2, scheme=Scheme.decimal)
    })
    tooltip_header.update({
        "total_cost": ["", element.description]
    })
    df_agg = df_agg.rename(columns={"value": "total_cost"}).set_index(["responseoption_id", "responseoption__name"])
    results = pd.concat([results, df_agg["total_cost"]], axis=1)

    # read all element values
    for element_pk in element_pks:
        element = Variable.objects.get(pk=element_pk)

        # read results for element
        df, df_cost, df_agg, df_cost_agg, agg_text, agg_unit, divider_text = read_results(
            element_pk=element_pk, scenario_pks=scenario_pks, response_pks=response_pks,
        )
        eff_unit = "1" if agg_unit == "1000 FCFA" else f"{agg_unit} / {divider_text} FCFA"

        # add columns to table
        scheme = Scheme.percentage_rounded if element.unit == "1" else Scheme.decimal
        columns.extend([
            {"id": f"{element_pk}_abs",
             "name": [f"{element.label}, {agg_text}", f"Abs.\n({agg_unit})"],
             "type": 'numeric',
             "format": Format(precision=2, scheme=scheme)},
            {"id": f"{element_pk}_change",
             "name": [f"{element.label}, {agg_text}", f"+/-\n({agg_unit})"],
             "type": 'numeric',
             "format": Format(precision=2, scheme=scheme, sign=Sign.positive)},
            {"id": f"{element_pk}_costeff",
             "name": [f"{element.label}, {agg_text}", f"+/- par coût\n({eff_unit})"],
             "type": 'numeric',
             "format": Format(precision=2, scheme=scheme, sign=Sign.positive)},
        ])

        agg_tooltip = ""
        if element.aggregate_by == "MEAN":
            agg_tooltip = """
            En moyenne sur la durée de la simulation.
            """
        elif element.aggregate_by == "SUM":
            agg_tooltip = """
            Sommé sur la durée de la simulation.
            """
        elif element.aggregate_by == "CHANGE":
            agg_tooltip = """
            Présenté ici : le changement de la valeur entre le début et la fin de la simulation.
            """
        elif element.aggregate_by == "%CHANGE":
            agg_tooltip = """
            Présenté ici : le changement fractionel de la valeur entre le début et la fin de la simulation.
            """

        element_tooltip = element.description if element.description is not None else ""
        element_tooltip += agg_tooltip

        abs_tooltip = """
        La valeur absolue de cet élément pour cette réponse.
        """
        change_tooltip = """
        La différence entre la valeur pour cette cette réponse, et la valeur pour "Aucune réponse".
        Si positive, la valeur est plus haut pour cette réponse que pour "Aucune réponse". 
        """
        costeff_tooltip = """
        La rapport coût-efficacité entre "Aucune réponse" et cette réponse. 
        Calculé comme la différence des valeurs divisée par les coûts totaux de cette réponse.
        Le plus haut que c'est, le plus d'impact cette réponse a sur cet élément par FCFA.
        """

        tooltip_header.update({
            f"{element_pk}_abs": [element_tooltip, abs_tooltip],
            f"{element_pk}_change": [element_tooltip, change_tooltip],
            f"{element_pk}_costeff": [element_tooltip, costeff_tooltip],
        })

        # format results and add them to table
        df_agg = df_agg[["responseoption_id", "responseoption__name", "value", "baseline_diff", "cost_eff"]]
        df_agg = df_agg.rename(columns={"value": f"{element_pk}_abs",
                                        "baseline_diff": f"{element_pk}_change",
                                        "cost_eff": f"{element_pk}_costeff",
                                        "responseoption_id": "id"})
        df_agg = df_agg.set_index(["id", "responseoption__name"])
        results = pd.concat([results, df_agg], axis=1)

    results = results.reset_index().rename(columns={"level_0": "id", "level_1": "responseoption__name"})
    results = results.replace([np.inf, -np.inf], np.nan)
    data = results.to_dict("records")

    # add response tooltips
    tooltip_data = [
        {"responseoption__name": {"value": ResponseOption.objects.get(pk=row.get("id")).description}}
        for row in data
    ]

    # add conditional formatting based on value of cell (compared to max and min of column)
    heat_map_styles = discrete_background_color_bins(results)
    style_data_conditional.extend(heat_map_styles)

    return data, columns, tooltip_header, tooltip_data, style_data_conditional


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

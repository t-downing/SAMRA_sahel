from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from ..models import ResponseOption, SimulatedDataPoint, Element


import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

initial_response1 = 1
initial_response2 = 2
initial_element1 = 15
initial_element2 = 39

ROWSTYLE = {"margin-bottom": "10px"}

app = DjangoDash("comparison", external_stylesheets=[dbc.themes.BOOTSTRAP])

responses_dropdown = [{"label": response.name, "value": response.pk} for response in ResponseOption.objects.all()]
elements_dropdown = [{"label": element.label, "value": element.pk}
                     for element in Element.objects.exclude(simulateddatapoints=None)]

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Comparer des réponses"),
                dbc.CardBody([
                    dbc.Checklist(
                        options=responses_dropdown,
                        value=[initial_response1, initial_response2],
                        id="response-input",
                        style={"margin-bottom": "20px"}
                    ),
                    dbc.InputGroup([
                       dbc.InputGroupText(["Élé. 1"]),
                       dbc.Select(id="element1-input", options=elements_dropdown, placeholder="Élément", value=initial_element1),
                    ], size="sm", style={"margin-bottom": "8px"}),
                    dbc.InputGroup([
                       dbc.InputGroupText(["Élé. 2"]),
                       dbc.Select(id="element2-input", options=elements_dropdown, placeholder="Élément", value=initial_element2),
                    ], size="sm"),
                ]),
            ]),
        ], width=2),
        dbc.Col([
            dcc.Graph(id="bar-graph", style={"height": "800px"})
        ], width=4),
        dbc.Col([
            dcc.Graph(id="line-graph", style={"height": "800px"})
        ], width=6),
    ], style={"margin-bottom": 40}),
    html.Hr(),
    dbc.Row([
        dbc.Col([
           dbc.Card([
               dbc.CardHeader("Construire une réponse"),
               dbc.CardBody([
                   dbc.Row([
                       dbc.Col(dbc.Select(id="build-response-input", options=responses_dropdown, value=initial_response2)),
                       dbc.Col(html.P("ou")),
                       dbc.Col(dbc.InputGroup([
                           dbc.Input(id="create-response-input"),
                           dbc.Button("Saisir", id="create-response-submit"),
                       ])),
                       html.Div(id="response-constants"),
                   ]),
               ]),
           ]),
        ], width=6),
    ]),
    dcc.Store(id="df-store"),
], fluid=True)


@app.callback(
    Output("build-response-input", "value"),
    Input("constantvalue-submit", "n_clicks"),
    State("constantvalue-element-input", "value"),
    State("constantvalue-value-input", "value"),
    State("build-response-input", "value"),
)
def create_constantvalue(_, element_pk, value, response_pk):
    if None in [element_pk, value, response_pk]:
        raise PreventUpdate
    response = ResponseOption.objects.get(pk=response_pk)
    element = Element.objects.get(pk=element_pk)



@app.callback(
    Output("response-constants", "children"),
    Input("build-response-input", "value"),
)
def build_response(response_pk):
    response = ResponseOption.objects.get(pk=response_pk)
    table_header = [html.Thead(html.Tr([html.Th("Élément"), html.Th("Valeur"), html.Th("Unité"), html.Th()]))]
    table_rows = []
    for constantvalue in response.constantvalues.all():
        table_rows.append(html.Tr([
            html.Td(constantvalue.element.label),
            html.Td(dbc.InputGroup([
                dbc.Input(value=constantvalue.value, id=f"constantvalue-{constantvalue.pk}-changevalue-input"),
                dbc.Button("Changer", id=f"constantvalue-{constantvalue.pk}-changevalue-submit"),
            ], size="sm")),
            html.Td(constantvalue.element.unit),
            html.Td(dbc.Button("Supprimer", id=f"delete-constantvalue-{constantvalue.pk}", size="sm")),
        ]))

    table_rows.append(html.Tr([
        html.Td(dbc.Select(id="constantvalue-element-input", placeholder="Ajouter un élément",
                           options=[{"label": element.label, "value": element.pk}
                                    for element in Element.objects.filter(sd_type="Constant")])),
        html.Td(dbc.Input(id="constantvalue-value-input")),
        html.Td(),
        html.Td(dbc.Button("Saisir", id="constantvalue-submit", size="sm"))
    ]))

    return dbc.Table(table_header + [html.Tbody(table_rows)])




@app.callback(
    Output("bar-graph", "figure"),
    Input("df-store", "data")
)
def update_bar_graph(data):
    if not data:
        raise PreventUpdate
    df = pd.DataFrame(data)
    df = df.groupby(["responseoption_id", "element_id"]).mean().reset_index().sort_values("secondary_y")
    print(df)
    df["norm_value"] = df["value"] / df.groupby("element_id")["value"].transform(max)
    print(df)
    fig = go.Figure()
    fig.update_layout(template="simple_white", margin=go.layout.Margin(l=0, r=0, b=0, t=0))

    for responseoption_id in df["responseoption_id"].unique():
        responseoption = ResponseOption.objects.get(pk=responseoption_id)
        dff = df[df["responseoption_id"] == responseoption_id]
        fig.add_trace(go.Bar(
            name=responseoption.name,
            x=dff["element_id"].apply(lambda pk : Element.objects.get(pk=pk).label),
            y=dff["norm_value"],
            text=dff['value'].apply(lambda num : f'{num:.3}'),
        ))

    fig.update_layout(barmode="group")
    fig.update_xaxes(side="top", linewidth=0, tickwidth=0)
    fig.update_yaxes(visible=False)
    fig.add_hline(y=0, line_width=1, line_color="black", opacity=1)
    return fig


@app.callback(
    Output("df-store", "data"),
    Input("response-input", "value"),
    Input("element1-input", "value"),
    Input("element2-input", "value"),
)
def filter_data(response_pks, element1_pk, element2_pk):
    if None in [response_pks, element1_pk, element2_pk]:
        raise PreventUpdate
    element_pks = [element1_pk, element2_pk]
    df = pd.DataFrame(SimulatedDataPoint.objects.filter(
        responseoption_id__in=response_pks, element_id__in=element_pks).values())
    print(element_pks)
    df["secondary_y"] = df["element_id"].apply(lambda pk : True if str(pk) == str(element2_pk) else False)
    df = df.sort_values(["secondary_y", "responseoption_id"])
    return df.to_dict("records")


@app.callback(
    Output("line-graph", "figure"),
    Input("df-store", "data")
)
def update_line_graph(data):
    if not data:
        raise PreventUpdate

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.update_layout(template="simple_white", margin=go.layout.Margin(l=0, r=0, b=0))
    fig.update_xaxes(title_text="Date")

    df = pd.DataFrame(data)

    for element_id in df["element_id"].unique():
        element = Element.objects.get(pk=element_id)
        dff = df[df["element_id"] == element_id]
        secondary_y = True if dff["secondary_y"].iloc[0] == 1 else False
        fig.update_yaxes(title_text=f"{element.label} ({element.unit})", secondary_y=secondary_y)
        for response_id in dff["responseoption_id"].unique():
            dfff = dff[dff["responseoption_id"] == response_id]
            response = ResponseOption.objects.get(pk=response_id)
            fig.add_trace(go.Scatter(
                x=dfff["date"],
                y=dfff["value"],
                name=response.name,
                legendgroup="secondary" if secondary_y else "primary",
                legendgrouptitle_text=element.label,
                line=dict(dash="dash") if secondary_y else {},
            ), secondary_y=secondary_y)

    fig.update_layout(
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.9,
            xanchor="right",
            x=0.9,
        )
    )

    return fig

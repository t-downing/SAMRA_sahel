from django_plotly_dash import DjangoDash
from dash import html, dcc
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from sahel.models import ResponseOption, SimulatedDataPoint, Element, ConstantValue, PulseValue

from sahel.sd_model.model_operations import run_model, timer

import plotly.graph_objects as go
import plotly
from plotly.subplots import make_subplots
import pandas as pd

initial_response1 = 1
initial_response2 = 2
initial_element1 = 15
initial_element2 = 39

default_colors = plotly.colors.DEFAULT_PLOTLY_COLORS

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
        ], width=5),
        dbc.Col([
            dcc.Graph(id="scatter-graph", style={"height": "400px"}),
            dcc.Graph(id="line-graph", style={"height": "400px"}),
        ], width=5),
    ], style={"margin-bottom": 40}),
    html.Hr(),
    dbc.Row([
        dbc.Col([
           dbc.Card([
               dbc.CardHeader("Construire une réponse"),
               dbc.CardBody([
                   dbc.InputGroup([
                       dbc.InputGroupText("Modifier une réponse"),
                       dbc.Select(id="build-response-input", options=responses_dropdown, value=initial_response2),
                   ]),
                   dcc.Loading(html.Div(id="response-constants")),
                   html.P("OU", style={"margin": "20px", "text-align": "center"}),
                   dbc.InputGroup([
                       dbc.InputGroupText("Créer une nouvelle réponse"),
                       dbc.Input(id="create-response-input", placeholder="Nom de réponse"),
                       dbc.Button("Saisir", id="create-response-submit", color="success"),
                   ]),
               ]),
           ]),
        ], width=6),
    ]),
    dcc.Store(id="df-store"),
    html.Div(id="constantvalue-deleted-readout"),
    html.Div(id="constantvalue-changed-readout"),
    html.Div(id="pulse-deleted-readout"),
    html.Div(id="pulse-changed-readout"),
    html.Div(id="constantvalue-added-readout")
], fluid=True)


@app.callback(
    Output("build-response-input", "options"),
    Output("build-response-input", "value"),
    Output("build-input", "value"),
    Input("create-response-submit", "n_clicks"),
    State("create-response-input", "value"),
)
def create_response(_, value):
    if value is None:
        raise PreventUpdate
    response = ResponseOption(name=value)
    response.save()
    responses_dropdown = [{"label": response.name, "value": response.pk} for response in ResponseOption.objects.all()]
    return responses_dropdown, response.pk, responses_dropdown


@app.callback(
    Output("constantvalue-added-readout", "children"),
    Input("constantvalue-submit", "n_clicks"),
    State("constantvalue-element-input", "value"),
    State("constantvalue-value-input", "value"),
    State("constantvalue-date-input", "date"),
    State("build-response-input", "value"),
)
def create_constantvalue(n_clicks, element_pk, value, date, response_pk):
    if None in [n_clicks, element_pk, value, response_pk]:
        raise PreventUpdate
    element = Element.objects.get(pk=element_pk)
    if element.sd_type == "Constant":
        ConstantValue(responseoption_id=response_pk, element_id=element_pk, value=value).save()
    elif element.sd_type == "Pulse Input":
        print(date)
        PulseValue(responseoption_id=response_pk, element_id=element_pk, value=value, startdate=date).save()
    run_model(responseoption_pk=response_pk)
    return f"created {element.sd_type} value with value {value}"


@app.callback(
    Output("constantvalue-deleted-readout", "children"),
    Input({"type": "constantvalue-delete", "index": ALL}, "n_clicks"),
    State({"type": "constantvalue-delete", "index": ALL}, "id"),
)
def delete_constantvalue(n_clicks, ids):
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            constantvalue = ConstantValue.objects.get(pk=id.get("index"))
            constantvalue.delete()
            run_model(responseoption_pk=constantvalue.responseoption.pk)
            return f"{id} deleted, RERUN MODEL"
    raise PreventUpdate


@app.callback(
    Output("pulse-deleted-readout", "children"),
    Input({"type": "pulse-delete", "index": ALL}, "n_clicks"),
    State({"type": "pulse-delete", "index": ALL}, "id"),
)
def delete_pulse(n_clicks, ids):
    for n_click, id in zip(n_clicks, ids):
        if n_click is not None:
            pulsevalue = PulseValue.objects.get(pk=id.get("index"))
            pulsevalue.delete()
            run_model(responseoption_pk=pulsevalue.responseoption.pk)
            return f"{id} deleted, RERUN MODEL"
    raise PreventUpdate


@app.callback(
    Output("constantvalue-changed-readout", "children"),
    Input({"type": "constantvalue-change", "index": ALL}, "n_clicks"),
    State({"type": "constantvalue-change", "index": ALL}, "id"),
    State({"type": "constantvalue-change-input", "index": ALL}, "value"),
)
def change_constantvalue(n_clicks, ids, values):
    for n_click, id, value in zip(n_clicks, ids, values):
        if n_click is not None:
            if value is not None:
                constantvalue = ConstantValue.objects.get(pk=id.get("index"))
                constantvalue.value = value
                constantvalue.save()
                run_model(responseoption_pk=constantvalue.responseoption.pk)
                return f"{constantvalue} changed"
    raise PreventUpdate


@app.callback(
    Output("pulse-changed-readout", "children"),
    Input({"type": "pulse-change", "index": ALL}, "n_clicks"),
    State({"type": "pulse-change", "index": ALL}, "id"),
    State({"type": "pulse-change-input", "index": ALL}, "value"),
)
def change_pulsevalue(n_clicks, ids, values):
    for n_click, id, value in zip(n_clicks, ids, values):
        if n_click is not None:
            if value is not None:
                pulsevalue = PulseValue.objects.get(pk=id.get("index"))
                pulsevalue.value = value
                pulsevalue.save()
                run_model(responseoption_pk=pulsevalue.responseoption.pk)
                return f"{pulsevalue} changed"
    raise PreventUpdate


@app.callback(
    Output("response-constants", "children"),
    Input("build-response-input", "value"),
    Input("constantvalue-deleted-readout", "children"),
    Input("constantvalue-added-readout", "children"),
    Input("constantvalue-changed-readout", "children"),
    Input("pulse-deleted-readout", "children"),
    Input("pulse-changed-readout", "children"),
)
def build_response(response_pk, *_):
    response = ResponseOption.objects.get(pk=response_pk)
    table_header = [html.Thead(html.Tr([
        html.Th("Élément"), html.Th("Valeur"), html.Th("Unité"), html.Th("Date"), html.Th()
    ]))]
    table_rows = []
    for constantvalue in response.constantvalues.all():
        table_rows.append(html.Tr([
            html.Td(constantvalue.element.label),
            html.Td(dbc.InputGroup([
                dbc.Input(value=constantvalue.value, id={"type": "constantvalue-change-input", "index": constantvalue.pk}),
                dbc.Button("Changer", id={"type": "constantvalue-change", "index": constantvalue.pk}),
            ], size="sm")),
            html.Td(constantvalue.element.unit),
            html.Td("N/A", style={"color": "gray"}),
            html.Td(dbc.Button("Supprimer", id={"type": "constantvalue-delete", "index": constantvalue.pk}, size="sm",
                               color="danger", outline=True)),
        ]))

    for pulsevalue in response.pulsevalues.all():
        table_rows.append(html.Tr([
            html.Td(pulsevalue.element.label),
            html.Td(dbc.InputGroup([
                dbc.Input(value=pulsevalue.value,
                          id={"type": "pulse-change-input", "index": pulsevalue.pk}),
                dbc.Button("Changer", id={"type": "pulse-change", "index": pulsevalue.pk}),
            ], size="sm")),
            html.Td(pulsevalue.element.unit),
            html.Td(pulsevalue.startdate),
            html.Td(dbc.Button("Supprimer", id={"type": "pulse-delete", "index": pulsevalue.pk}, size="sm",
                               color="danger", outline=True)),
        ]))

    table_rows.append(html.Tr([
        html.Td(dcc.Dropdown(id="constantvalue-element-input", placeholder="Ajouter un élément",
                           options=[{"label": element.label, "value": element.pk}
                                    for element in Element.objects.filter(sd_type__in=["Constant", "Pulse Input"])])),
        html.Td(dbc.Input(id="constantvalue-value-input")),
        html.Td(id="constantvalue-unit-input"),
        html.Td(dcc.DatePickerSingle(id="constantvalue-date-input")),
        html.Td(dbc.Button("Saisir", id="constantvalue-submit", size="sm"))
    ]))

    return dbc.Table(table_header + [html.Tbody(table_rows)])


@app.callback(
    Output("constantvalue-unit-input", "children"),
    Input("constantvalue-element-input", "value")
)
def show_constantvalue_unit(element_pk):
    if element_pk is None:
        raise PreventUpdate
    return Element.objects.get(pk=element_pk).unit


@app.callback(
    Output("df-store", "data"),
    Input("response-input", "value"),
    Input("element1-input", "value"),
    Input("element2-input", "value"),
    Input("constantvalue-deleted-readout", "children"),
    Input("constantvalue-added-readout", "children"),
    Input("constantvalue-changed-readout", "children"),
)
@timer
def filter_data(response_pks, element1_pk, element2_pk, *_):
    if None in [response_pks, element1_pk, element2_pk]:
        raise PreventUpdate
    element_pks = [element1_pk, element2_pk]
    df = pd.DataFrame(SimulatedDataPoint.objects.filter(
        responseoption_id__in=response_pks, element_id__in=element_pks).values())
    response_pk2color = {response_pk: color for response_pk, color in zip(response_pks, default_colors)}
    df["color"] = df["responseoption_id"].apply(response_pk2color.get)
    df["secondary_y"] = df["element_id"].apply(lambda pk : True if str(pk) == str(element2_pk) else False)
    df = df.sort_values(["responseoption_id", "secondary_y"])
    return df.to_dict("records")


@app.callback(
    Output("bar-graph", "figure"),
    Input("df-store", "data")
)
@timer
def update_bar_graph(data):
    if not data:
        raise PreventUpdate
    df = pd.DataFrame(data)
    df = df.groupby(["responseoption_id", "element_id"]).agg(mean=("value", "mean"), sum=("value", "sum"), secondary_y=("secondary_y", "mean")).reset_index()
    # df = df.groupby(["responseoption_id", "element_id"]).mean().reset_index()
    df["value"] = df[["element_id", "mean", "sum"]].apply(
        lambda row : row["mean"] if Element.objects.get(pk=row["element_id"]).aggregate_by == "MEAN" else row["sum"], axis=1)
    df["norm_value"] = df["value"] / df.groupby("element_id")["value"].transform(max)
    df = df.sort_values("secondary_y")

    fig = go.Figure()
    fig.update_layout(template="simple_white", margin=go.layout.Margin(l=0, r=0, b=0, t=0))

    for responseoption_id in df["responseoption_id"].unique():
        responseoption = ResponseOption.objects.get(pk=responseoption_id)
        dff = df[df["responseoption_id"] == responseoption_id]
        fig.add_trace(go.Bar(
            name=responseoption.name,
            x=dff["element_id"].apply(
                lambda pk : f"{Element.objects.get(pk=pk).label}<br>"
                            f"{'MOYEN' if Element.objects.get(pk=pk).aggregate_by == 'MEAN' else 'TOTAL'}"),
            y=dff["norm_value"],
            text=dff[["value", "element_id"]].apply(
                lambda row : f'{row["value"]:.2}<br>{Element.objects.get(pk=row["element_id"]).unit}', axis=1),
        ))

    fig.update_layout(barmode="group", showlegend=True, legend=dict(title="Réponse"))
    fig.update_xaxes(side="top", showline=False, ticklen=0)
    fig.update_yaxes(visible=False)
    fig.add_hline(y=0, line_width=1, line_color="black", opacity=1)
    return fig


@app.callback(
    Output("scatter-graph", "figure"),
    Input("df-store", "data"),
)
@timer
def update_scatter_graph(data):
    if not data: raise PreventUpdate

    df = pd.DataFrame(data)

    fig = go.Figure()
    fig.update_layout(template="simple_white", margin=go.layout.Margin(l=0, b=0))

    df = df.groupby(["responseoption_id", "element_id"]).agg(mean=("value", "mean"), sum=("value", "sum"), secondary_y=("secondary_y", "mean")).reset_index()
    df = df.sort_values("secondary_y")
    print(df)
    x_element = Element.objects.get(pk=df.iloc[-1]["element_id"])
    y_element = Element.objects.get(pk=df.iloc[0]["element_id"])
    df["value"] = df[["element_id", "mean", "sum"]].apply(
        lambda row: row["mean"] if Element.objects.get(pk=row["element_id"]).aggregate_by == "MEAN" else row["sum"],
        axis=1)
    df = df.pivot(index="responseoption_id", columns="element_id", values="value").reset_index()
    print(df)

    [x_agg, y_agg] = ["MOYEN" if element.aggregate_by == "MEAN" else "TOTAL" for element in [x_element, y_element]]

    for response_id in df["responseoption_id"].unique():
        response = ResponseOption.objects.get(pk=response_id)
        dff = df[df["responseoption_id"] == response_id]
        fig.add_trace(go.Scatter(
            x=dff.iloc[:][x_element.pk],
            y=dff.iloc[:][y_element.pk],
            text=response.name,
            mode="markers+text",
            textposition="middle right",
            marker_size=10,
        ))

    fig.update_layout(showlegend=False, title_text=f"{y_element.label} vs. {x_element.label}")
    fig.update_xaxes(title_text=f"{x_element.label} {x_agg} ({x_element.unit})", rangemode="tozero")
    fig.update_yaxes(title_text=f"{y_element.label} {y_agg} ({y_element.unit})", rangemode="tozero")
    return fig


@app.callback(
    Output("line-graph", "figure"),
    Input("df-store", "data")
)
@timer
def update_line_graph(data):
    if not data: raise PreventUpdate

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
                line_color=dfff["color"].iloc[0]
            ), secondary_y=secondary_y)

    fig.update_layout(
        showlegend=True,
        legend=dict(yanchor="top", y=0.9, xanchor="right", x=0.9, bgcolor='rgba(255,255,255,0.5)', font=dict(size=10),
                    grouptitlefont=dict(size=11)),
        title_text="Chronologie",
    )

    return fig

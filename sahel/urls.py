from django.urls import path, include
from . import views


urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("model_diagram", views.ModelDiagramView.as_view(), name="model_diagram"),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
    path("equation_bank", views.EquationBankView.as_view(), name="equation_bank"),
    path("responses", views.ResponseView.as_view(), name="responses"),
    path("scenarios", views.ScenarioView.as_view(), name="scenarios"),
    path("forecasts", views.ForecastView.as_view(), name="forecasts"),
    path("sources", views.SourceListView.as_view(), name="sources"),
    path("scenarioresponse", views.ScenarioResponseView.as_view(), name="scenarioresponse"),
    path("termsoftrade", views.TermsOfTradeView.as_view(), name="termsoftrade"),
    path("response_list", views.ResponseListView.as_view(), name="response_list"),
    path("mapping2modeling", views.Mapping2Modeling.as_view(), name="mapping2modeling"),
    path("evidencebit/create", views.EBCreateView.as_view(), name="eb_create"),
]
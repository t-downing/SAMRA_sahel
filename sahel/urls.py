from django.urls import path, include
from . import views


urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("model_diagram", views.ModelDiagramView.as_view(), name="model_diagram"),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
    path("equation_bank", views.EquationBankView.as_view(), name="equation_bank"),
    path("comparison", views.ComparisonView.as_view(), name="comparison"),
    path("scenarios", views.ScenarioView.as_view(), name="scenarios"),
]
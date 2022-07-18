from django.urls import path, include
from . import views


urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("model_diagram", views.ModelDiagramView.as_view(), name="model_diagram"),
    path("django_plotly_dash/", include("django_plotly_dash.urls")),
]
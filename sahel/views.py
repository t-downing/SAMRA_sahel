from django.views.generic import TemplateView, ListView
from .models import Source

# for some reason the line below needs to be commented out when running makemigrations
from .sd_model import dash_schema, dash_comparison, dash_forecasts


class IndexView(TemplateView):
    template_name = "sahel/index.html"


class ModelDiagramView(TemplateView):
    template_name = "sahel/model_diagram.html"


class ComparisonView(TemplateView):
    template_name = "sahel/comparison.html"


class ScenarioView(TemplateView):
    template_name = "sahel/scenarios.html"


class EquationBankView(TemplateView):
    template_name = "sahel/equation_bank.html"


class SourceListView(ListView):
    template_name = "sahel/sources.html"
    model = Source

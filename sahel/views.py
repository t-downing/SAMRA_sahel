from django.views.generic import TemplateView, ListView
from .models import Source

from .sd_model import dash_schema, dash_comparison, dash_forecasts, dash_scenarioresponse, dash_response_builder


class IndexView(TemplateView):
    template_name = "sahel/index.html"


class ModelDiagramView(TemplateView):
    template_name = "sahel/model_diagram.html"


class ComparisonView(TemplateView):
    template_name = "sahel/comparison.html"


class ScenarioView(TemplateView):
    template_name = "sahel/scenarios.html"


class ScenarioResponseView(TemplateView):
    template_name = "sahel/scenarioresponse.html"


class EquationBankView(TemplateView):
    template_name = "sahel/equation_bank.html"


class SourceListView(ListView):
    template_name = "sahel/sources.html"
    model = Source

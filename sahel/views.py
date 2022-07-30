from django.views.generic import TemplateView

# for some reason the line below needs to be commented out when running makemigrations
from .sd_model import dash_schema, dash_comparison

class IndexView(TemplateView):
    template_name = "sahel/index.html"


class ModelDiagramView(TemplateView):
    template_name = "sahel/model_diagram.html"


class ComparisonView(TemplateView):
    template_name = "sahel/comparison.html"


class EquationBankView(TemplateView):
    template_name = "sahel/equation_bank.html"

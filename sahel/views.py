from django.shortcuts import render
from django.views.generic import TemplateView
from . import dash_app
from .dash_app import comparison


class IndexView(TemplateView):
    template_name = "sahel/index.html"


class ModelDiagramView(TemplateView):
    template_name = "sahel/model_diagram.html"


class ComparisonView(TemplateView):
    template_name = "sahel/comparison.html"


class EquationBankView(TemplateView):
    template_name = "sahel/equation_bank.html"

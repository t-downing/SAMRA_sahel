from django.shortcuts import render
from django.views.generic import TemplateView
from . import dash_app


class IndexView(TemplateView):
    template_name = "sahel/index.html"


class ModelDiagramView(TemplateView):
    template_name = "sahel/model_diagram.html"

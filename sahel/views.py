from django.views.generic import TemplateView, ListView, CreateView
from .models import Source, EvidenceBit, Element
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets
from .serializers import ElementSerializer

from .sd_model import dash_schema, dash_comparison, dash_forecasts, dash_scenarioresponse, dash_response_builder, \
    dash_termsoftrade, dash_response_list, dash_mapping2modeling


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/index.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class ModelDiagramView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/model_diagram.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class ResponseView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/responses.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class ScenarioView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/responses.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class ForecastView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/forecasts.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class ScenarioResponseView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/scenarioresponse.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class TermsOfTradeView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/termsoftrade.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class ResponseListView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/responses_list.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class EquationBankView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/equation_bank.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class SourceListView(LoginRequiredMixin, ListView):
    template_name = "sahel/sources.html"
    model = Source
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class Mapping2Modeling(LoginRequiredMixin, TemplateView):
    template_name = "sahel/mapping2modeling.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class EBCreateView(LoginRequiredMixin, CreateView):
    template_name = "sahel/eb_create.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    model = EvidenceBit
    fields = ["content", "eb_date", "source", "elements"]


class ElementViewSet(viewsets.ModelViewSet):
    queryset = Element.objects.all()
    serializer_class = ElementSerializer

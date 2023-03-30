from django.views.generic import TemplateView, ListView, CreateView
from .models import Source, EvidenceBit
from django.contrib.auth.mixins import LoginRequiredMixin
import os

from .sd_model import dash_schema, dash_comparison, dash_forecasts, dash_scenarioresponse, dash_response_builder, \
    dash_termsoftrade, dash_response_list, dash_mapping2modeling, dash_dataexplorer


class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/index.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class ModelDiagramView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/model_diagram.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class ResponseView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/responses.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class ScenarioView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/responses.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class ForecastView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/forecasts.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class ScenarioResponseView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/scenarioresponse.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class TermsOfTradeView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/termsoftrade.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class ResponseListView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/responses_list.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class EquationBankView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/equation_bank.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class SourceListView(LoginRequiredMixin, ListView):
    template_name = "sahel/sources.html"
    model = Source
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class Mapping2Modeling(LoginRequiredMixin, TemplateView):
    template_name = "sahel/mapping2modeling.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class EBCreateView(LoginRequiredMixin, CreateView):
    template_name = "sahel/eb_create.html"
    model = EvidenceBit
    fields = ["content", "eb_date", "source", "elements"]
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'


class DataExplorerView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/dataexplorer.html"
    if os.environ.get("USE_PSQL") == "yes":
        login_url = '/accounts/login/'
        redirect_field_name = 'next'

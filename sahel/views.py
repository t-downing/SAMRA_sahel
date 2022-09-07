from django.views.generic import TemplateView, ListView
from .models import Source
from django.contrib.auth.mixins import LoginRequiredMixin

from .sd_model import dash_schema, dash_comparison, dash_forecasts, dash_scenarioresponse, dash_response_builder, \
    dash_termsoftrade, dash_response_list


class IndexView(TemplateView):
    template_name = "sahel/index.html"


class ModelDiagramView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/model_diagram.html"
    login_url = '/accounts/login/'
    redirect_field_name = 'next'


class ComparisonView(LoginRequiredMixin, TemplateView):
    template_name = "sahel/comparison.html"
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

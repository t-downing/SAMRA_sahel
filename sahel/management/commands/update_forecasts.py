from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element
import pandas as pd


class Command(BaseCommand):
    help = 'Updates forecasts for given variable'

    def add_arguments(self, parser):
        parser.add_argument('-e', '--variablepks', nargs='+', type=int, help="variable pks to be forecasted")
        parser.add_argument('-a', '--admin0', nargs='?', type=str, help="admin0 to be forecasted")
        parser.add_argument('-t', '--all', action='store_true')

    def handle(self, *args, **options):
        variable_pks = options['variablepks']
        admin0 = options['admin0'] if options['admin0'] is not None else 'Mauritanie'
        if options['all']:
            variable_pks = [variable.pk for variable in Variable.objects.filter(sd_type=Variable.INPUT)]
        if variable_pks is not None:
            for variable_pk in variable_pks:
                forecast_element(variable_pk, admin0)
        return

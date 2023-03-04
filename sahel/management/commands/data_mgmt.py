from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element
import pandas as pd


class Command(BaseCommand):
    def handle(self, *args, **options):
        pks = [248, 249, 250]
        mdps = MeasuredDataPoint.objects.filter(pk__in=pks)
        for mdp in mdps:
            value = mdp.value / 50

        pass




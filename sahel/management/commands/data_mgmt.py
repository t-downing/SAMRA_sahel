from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element
import pandas as pd


class Command(BaseCommand):
    def handle(self, *args, **options):
        MeasuredDataPoint.objects.filter(date=date(2020, 5, 15), element_id=131).delete()
        pass




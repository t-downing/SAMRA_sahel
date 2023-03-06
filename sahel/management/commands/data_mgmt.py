from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element
import pandas as pd


class Command(BaseCommand):
    def handle(self, *args, **options):

        print(Variable.objects.filter(pk__in=[175, 77, 193, 13, 160]))

        pass




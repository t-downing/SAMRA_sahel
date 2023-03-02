from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element
import pandas as pd


class Command(BaseCommand):
    def handle(self, *args, **options):
        df = pd.DataFrame(ForecastedDataPoint.objects.filter(admin0='Mali').values('element__label'))
        print(df['element__label'].unique())
        pass




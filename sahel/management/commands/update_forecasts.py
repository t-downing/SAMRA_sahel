from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element
import pandas as pd


class Command(BaseCommand):
    def handle(self, *args, **options):
        admin0 = 'Mauritanie'
        # 42 - prix de bovin
        # 169 - pluv réel
        # df = pd.DataFrame(ForecastedDataPoint.objects.filter(admin0=admin0).values())
        # forecasted_pks = df['element_id'].unique()
        # print(forecasted_pks)
        alimentation_pks = [248, 249, 250]
        for variable in Variable.objects.filter(sd_type='Input', pk__in=alimentation_pks):
            forecast_element(variable.pk, admin0)
        # forecast_element(42, admin0)

        pass
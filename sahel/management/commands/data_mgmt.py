from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element
import pandas as pd


class Command(BaseCommand):
    def handle(self, *args, **options):
        sdps = SeasonalInputDataPoint.objects.all()
        objs = []
        for sdp in sdps:
            objs.append(SeasonalInputDataPoint(
                value=sdp.value,
                date=sdp.date,
                admin0='Mauritanie',
                element_id=sdp.element_id
            ))
        # SeasonalInputDataPoint.objects.bulk_create(objs)
        pass




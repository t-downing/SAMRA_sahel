from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element


class Command(BaseCommand):
    def handle(self, *args, **options):
        elements = Variable.objects.filter(sd_type="Input").exclude(measureddatapoints=None)
        for element in elements:
            print(element)
            forecast_element(element.pk)
        pass




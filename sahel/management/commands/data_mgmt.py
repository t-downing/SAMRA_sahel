from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element


class Command(BaseCommand):
    def handle(self, *args, **options):
        PulseValue.objects.all().update(admin0='Mali')

        pass




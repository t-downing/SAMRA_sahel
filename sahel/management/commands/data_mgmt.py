from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element


class Command(BaseCommand):
    def handle(self, *args, **options):
        count = 0
        for variable in Variable.objects.all():
            if not variable.unit == variable.unit.replace("FCFA", "LCY"):
                variable.unit = variable.unit.replace("FCFA", "LCY")
                variable.save()
        print(count)
        pass




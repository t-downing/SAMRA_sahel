from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element
import pandas as pd


class Command(BaseCommand):
    def handle(self, *args, **options):
        for variable in Variable.objects.all():
            if variable.element_id is not None:
                print(f"{variable} has element")
                if variable.element.element_group_id is not None:
                    print(f"{variable.element} has group")
                    variable.element_group_id = variable.element.element_group_id
                    variable.save()
        pass




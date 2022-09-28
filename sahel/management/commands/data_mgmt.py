from django.core.management.base import BaseCommand
from ... import models
from datetime import date


class Command(BaseCommand):
    def handle(self, *args, **options):
        for model in [models.ResponseOption, models.Scenario]:
            model.objects.all().update(samra_model_id=1)
        pass




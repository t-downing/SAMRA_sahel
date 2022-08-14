from django.core.management.base import BaseCommand
from ... import models
from sahel.sd_model.model_operations import run_model


class Command(BaseCommand):
    def handle(self, *args, **options):
        scenarios = models.Scenario.objects.all()
        responses = models.ResponseOption.objects.all()

        for scenario in scenarios:
            for response in responses:
                run_model(scenario.pk, response.pk)





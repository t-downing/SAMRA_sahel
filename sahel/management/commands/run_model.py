from django.core.management.base import BaseCommand
from ... import models
from sahel.sd_model.model_operations import run_model
import time


class Command(BaseCommand):
    def handle(self, *args, **options):
        scenarios = models.Scenario.objects.filter(pk=1)
        responses = models.ResponseOption.objects.filter(pk=1)

        total = len(scenarios) * len(responses)
        count = 0
        for scenario in scenarios:
            for response in responses:
                start = time.time()
                run_model(scenario.pk, response.pk)
                duration = time.time() - start
                count += 1
                eta = duration * (total - count)
                print(f"Progress: {round(count / total, 3)}; ETA: {round(eta)} s")







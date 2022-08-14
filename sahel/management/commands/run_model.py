from django.core.management.base import BaseCommand
from ... import models
from sahel.sd_model.model_operations import run_model
import time


class Command(BaseCommand):
    def handle(self, *args, **options):
        scenarios = models.Scenario.objects.all()
        responses = models.ResponseOption.objects.all()

        count = 0

        start = time.time()
        for scenario in scenarios:
            for response in responses:
                run_model(scenario.pk, response.pk)
                count += 1
        duration = time.time() - start
        print(f"Count: {count}, Total time: {duration:.2f} s, Time per run: {duration / count :2.f} s")





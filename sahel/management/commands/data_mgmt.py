from django.core.management.base import BaseCommand
from ... import models


class Command(BaseCommand):
    def handle(self, *args, **options):
        models.SimulatedDataPoint.objects.filter(old_scenario__isnull=False).delete()




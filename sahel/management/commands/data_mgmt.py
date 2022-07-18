from django.core.management.base import BaseCommand
from ... import models


class Command(BaseCommand):
    def handle(self, *args, **options):
        models.SimulatedDataPoint.objects.filter(value=0.0).delete()

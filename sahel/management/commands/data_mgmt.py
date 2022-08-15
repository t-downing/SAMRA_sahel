from django.core.management.base import BaseCommand
from ... import models


class Command(BaseCommand):
    def handle(self, *args, **options):
        sum_elements = models.Element.objects.filter(label__contains="Revenu")
        sum_elements.update(aggregate_by="SUM")




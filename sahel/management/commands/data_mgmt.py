from django.core.management.base import BaseCommand
from ... import models
from datetime import date


class Command(BaseCommand):
    def handle(self, *args, **options):
        source = models.Source.objects.get(pk=1)
        del_objs = models.MeasuredDataPoint.objects.filter(source=source, element_id=131)
        print(len(del_objs))




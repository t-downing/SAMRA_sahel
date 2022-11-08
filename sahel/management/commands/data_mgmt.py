from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date


class Command(BaseCommand):
    def handle(self, *args, **options):
        Element.objects.filter(samramodel_id__isnull=True).update(samramodel_id=2)
        pass




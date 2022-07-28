from django.core.management.base import BaseCommand
from ... import models


class Command(BaseCommand):
    def handle(self, *args, **options):
        print(models.Element.objects.get(pk=100).sd_type)




from django.core.management.base import BaseCommand
import django.apps
from sahel.models import *


class Command(BaseCommand):
    def handle(self, *args, **options):
        for model in django.apps.apps.get_models():
            print(model.__name__)
            objs = model.objects.all()
            print(f"obj count: {len(objs)}")

            model.objects.using("local").bulk_create(objs)

        pass
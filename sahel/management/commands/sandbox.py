from django.core.management.base import BaseCommand
from ...dash_app.sd_model import run_model


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("HELLO")
        df = run_model()
        print(df)
from django.core.management.base import BaseCommand
from ...dash_app.run_model import run_model
import pandas as pd
from ...models import Element, SimulatedDataPoint
from datetime import date
from ... import dash_app


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("HELLO running sandbox")
        run_model()
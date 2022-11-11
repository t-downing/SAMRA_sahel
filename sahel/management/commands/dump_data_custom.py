from django.core.management.base import BaseCommand
import django.apps
from sahel.models import *
import sys
from django.core.management import call_command


class Command(BaseCommand):
    def handle(self, *args, **options):
        exclude = [
            'sahel.MeasuredDataPoint',
            'sahel.SimulatedDataPoint',
            'sahel.ForecastedDataPoint',
        ]
        with open('output_files/custom_dump.json', 'w'):
            call_command('dumpdata', 'sahel', exclude=exclude, stdout='f')
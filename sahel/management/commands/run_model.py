from django.core.management.base import BaseCommand
from ... import models
from sahel.sd_model.model_operations import run_model
import time


class Command(BaseCommand):
    help = 'Runs model for given model, response, scenario, admin0'

    def add_arguments(self, parser):
        parser.add_argument('-s', '--scenariopks', nargs='+', type=int, help="scenario pks to be run")
        parser.add_argument('-r', '--responsepks', nargs='+', type=int, help="response pks to be run")
        parser.add_argument('-m', '--modelpk', nargs='?', type=int, help="model pk to be run")
        parser.add_argument('-a', '--admin0', nargs='?', type=str, help="admin0 to be run")

    def handle(self, *args, **options):
        scenario_pks = options['scenariopks'] if options['scenariopks'] is not None else [1]
        response_pks = options['responsepks'] if options['responsepks'] is not None else [1]
        model_pk = options['modelpk'] if options['modelpk'] is not None else 1
        admin0 = options['admin0'] if options['admin0'] is not None else 'Mauritanie'
        run_model(scenario_pks, response_pks, model_pk, admin0)
        return







from django.core.management.base import BaseCommand
from sahel.sd_model import model_operations


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("HELLO running sandbox")
        run_model()
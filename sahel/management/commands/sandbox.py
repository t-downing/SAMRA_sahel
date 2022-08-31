from django.core.management.base import BaseCommand
import math


class Command(BaseCommand):
    def handle(self, *args, **options):
        exec("a = 1", {}, {})
        locals()["a"] = 1
        exec("print(a)")



from django.core.management.base import BaseCommand
import math


class Command(BaseCommand):
    def handle(self, *args, **options):
        exec("print('hello')", {"__builtins__": None, "print": print})

        def smooth(input):
            return input + 5

        model_locals = {}
        model_locals.update({"dog": 50})
        model_locals.update({"cosine": math.cos})

        print(model_locals.get("dog"))

        exec("a = cosine", {"__builtins__": None, "math": math, "smooth": smooth}, model_locals)
        a = model_locals.get("a")
        print(a(1))




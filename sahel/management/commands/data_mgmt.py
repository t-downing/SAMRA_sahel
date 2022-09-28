from django.core.management.base import BaseCommand
from ... import models
from datetime import date


class Command(BaseCommand):
    def handle(self, *args, **options):
        story = models.Story.objects.get(pk=1)
        for variable in models.Variable.objects.all():
            print(variable)
            models.VariablePosition(
                variable=variable,
                story=story,
                x_pos=variable.x_pos,
                y_pos=variable.y_pos,
            ).save()
        pass




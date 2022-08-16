from django.core.management.base import BaseCommand
from sahel.sd_model import model_operations
from sahel.models import Element, ElementGroup, Source
from sahel import models
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
import time
import pmdarima as pm


class Command(BaseCommand):
    def handle(self, *args, **options):
        save_all_objects = False
        if save_all_objects:
            print("ELEMENT GROUPS")
            elementgroups = ElementGroup.objects.all()
            for elementgroup in elementgroups:
                print(elementgroup.label)
                elementgroup.save(using="remote")

            print("ELEMENTS - STOCKS")
            elements = Element.objects.filter(sd_type="Stock")
            for element in elements:
                print(element.label)
                element.save(using="remote")

            print("ELEMENTS - OTHER")
            elements = Element.objects.exclude(sd_type="Stock")
            for element in elements:
                print(element.label)
                element.save(using="remote")

            for obj in Source.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.Connection.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.Scenario.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.ResponseOption.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.ConstantValue.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.SeasonalInputDataPoint.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.PulseValue.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.ScenarioConstantValue.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.HouseholdConstantValue.objects.all():
                print(obj)
                obj.save(using="remote")

            for obj in models.RegularDataset.objects.all():
                print(obj)
                obj.save(using="remote")

            forecasteddatapoints = models.ForecastedDataPoint.objects.all()
            length = len(forecasteddatapoints)
            print(f"there are {length} objs")
            for index, obj in enumerate(forecasteddatapoints):
                print(f"{round(index / length, 3)}  progress; {obj}")
                obj.save(using="remote")

            objs = models.MeasuredDataPoint.objects.filter(date__gte="2020-01-01")
            length = len(objs)
            print(f"there are {length} objs")
            for index, obj in enumerate(objs):
                start = time.time()
                obj.save(using="remote")
                duration = time.time() - start
                eta = duration * (length - index)
                print(f"Progress: {round(index / length, 3)}; ETA: {round(eta)} s; obj: {obj}")

        pass

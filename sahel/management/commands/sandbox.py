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
        string = "print(5+5), print(time.time()), print(dir())"
        exec(string, {"time": time, "__builtins__": None}, {"print": print, "dir": dir})

        pass

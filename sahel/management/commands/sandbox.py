import datetime

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
from django.db import connection
from contextlib import closing


class Command(BaseCommand):
    def handle(self, *args, **options):
        df = pd.DataFrame([{"date": datetime.datetime(2000, 1, 1), "variable": 1, "value": 1.5},
                             {"date": datetime.datetime(2000, 1, 2), "variable": 1, "value": 1.6}])

        insert_stmt = (
            "INSERT INTO sahel_simulateddatapoint (element_id, value, date, scenario_id, responseoption_id) "
            f"VALUES {', '.join(['(%s, %s, %s, %s, %s)'] * len(df))}"
        )

        data = []

        for row in df.itertuples():
            data.extend([row.variable, row.value, row.date, 1, 1])

        print(data)

        with closing(connection.cursor()) as cursor:
            cursor.execute(insert_stmt, data)
        pass

from django.core.management.base import BaseCommand
from sahel.sd_model import model_operations
from ... import models
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
import time
import pmdarima as pm



class Command(BaseCommand):
    def handle(self, *args, **options):
        element = models.Element.objects.get(pk=62)
        df = pd.DataFrame(models.MeasuredDataPoint.objects.filter(element=element).values())
        df.index = pd.to_datetime(df["date"])
        df = df.resample('MS').mean().interpolate()["value"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df.values,
        ))
        stepwise_fit = pm.auto_arima(df, m=12, max_order=None)
        print(stepwise_fit.summary())
        print(stepwise_fit.get_params())
        print(stepwise_fit)
        n_periods = 36
        pred_dates = pd.date_range(df.index[-1] + pd.DateOffset(months=1), periods=n_periods, freq="MS")
        yhat = stepwise_fit.predict(n_periods=n_periods)
        print(yhat)
        print(pred_dates)
        fig.add_trace(go.Scatter(
            x=pred_dates,
            y=yhat,
            name="auto",
        ))

        orders = [
            ((0, 1, 13), (0, 1, 0, 12)),
            ((0, 2, 13), (0, 1, 0, 12)),
            ((1, 1, 13), (0, 1, 0, 12)),
            ((1, 2, 13), (0, 1, 0, 12)),
        ]
        for order in orders:
            model = SARIMAX(df, order=order[0], seasonal_order=order[1])
            model_fit = model.fit()
            print(f"AIC is {model_fit.aic}")
            yhat = model_fit.forecast(steps=n_periods)
            fig.add_trace(go.Scatter(
                x=yhat.index,
                y=yhat.values,
                name=f"({order[0][0]}, {order[0][1]}, {order[0][2]}), ({order[1][0]}, {order[1][1]}, {order[1][2]}, {order[1][3]})"
            ))
        fig.write_html("plotly_output.html")

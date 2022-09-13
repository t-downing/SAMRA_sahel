import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

from ..models import Variable, Source, ForecastedDataPoint


def forecast_element(element_pk, sarima_params=None):
    use_ets = True
    forecast_years = 2
    element = Variable.objects.get(pk=element_pk)
    df = pd.DataFrame(element.measureddatapoints.all().values())

    # determine correct periodicity
    if element.source_for_model is not None:
        df = df[df["source_id"] == element.source_for_model.pk]
        number_of_periods = element.source_for_model.number_of_periods
    elif Source.objects.get(pk=df["source_id"].iloc[0]).number_of_periods is not None or len(df["source_id"].unique()) > 1:
        number_of_periods = Source.objects.get(pk=df["source_id"].iloc[0]).number_of_periods
    else:
        number_of_periods = 12



    # resample into MS or QS (previously LIKELY on 15th of month etc)
    if number_of_periods == 12:
        period = "MS"
    elif number_of_periods == 4:
        period = "QS"
    elif number_of_periods == 36:
        period = f"{31556952 / 36}S"
    else:
        period = "MS"

    df.index = pd.to_datetime(df["date"])
    forecast_periods = number_of_periods * forecast_years

    objs = []
    for admin1 in df["admin1"].unique():
        print(f"FORECASTING {admin1} NOW")
        dff = df[df["admin1"] == admin1]
        dff = dff.resample(period).mean().interpolate()["value"]

        try:
            model = ETSModel(dff, error="add", trend="add", damped_trend=True, seasonal="add", seasonal_periods=number_of_periods)
        except:
            try:
                if element.unit == "1":
                    if len(dff) > number_of_periods - 1:
                        model = SARIMAX(dff, order=[0, 0, 0], seasonal_order=[0, 1, 0, number_of_periods])
                    else:
                        model = SARIMAX(dff, order=[0, 1, 0], seasonal_order=[0, 0, 0, 0])
                else:
                    model = ETSModel(dff, error="add", trend="add", damped_trend=True)
            except:
                try:
                    model = ETSModel(dff, error="add", trend="add")
                except:
                    model = ETSModel(dff, error="add")

        if Source.objects.get(pk=df["source_id"].iloc[0]).pk == 7:
            model = SARIMAX(dff, order=[1, 1, number_of_periods + 1], seasonal_order=[1, 1, 0, number_of_periods])
        model_fit = model.fit()
        forecast_points = model_fit.forecast(steps=forecast_periods)
        print(forecast_points)

        dateoffset = pd.DateOffset(months=2 if period == "QS" else 0, days=14 if period in ["QS", "MS"] else 10)

        # record and re-shift forward to 15th of month
        objs += [ForecastedDataPoint(
            element=element,
            admin1=admin1,
            date=date + dateoffset,
            value=value
        ) for date, value in forecast_points.iteritems()]

    ForecastedDataPoint.objects.filter(element=element).delete()
    ForecastedDataPoint.objects.bulk_create(objs)

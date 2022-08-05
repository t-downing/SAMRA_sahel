import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from ..models import Element, Source, ForecastedDataPoint


def forecast_element(element_pk):
    forecast_years = 2
    element = Element.objects.get(pk=element_pk)
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
    else:
        period = "MS"

    df.index = pd.to_datetime(df["date"])
    order = (0, 1, number_of_periods + 1)
    seasonal_order = (1, 0, 0, number_of_periods)
    forecast_periods = number_of_periods * forecast_years

    objs = []
    for admin1 in df["admin1"].unique():
        print(f"FORECASTING {admin1} NOW")
        dff = df[df["admin1"] == admin1]
        dff = dff.resample(period).mean().interpolate()["value"]
        print(len(dff))
        if len(dff) < number_of_periods:
            pass
        print(dff)
        try:
            model = SARIMAX(dff, order=order, seasonal_order=seasonal_order)
            model_fit = model.fit()
        except Exception as e:
            print(f"couldn't model because:\n{e}")
            continue

        forecast_points = model_fit.forecast(steps=forecast_periods)
        print(forecast_points)

        # record and re-shift forward to 15th of month
        objs += [ForecastedDataPoint(
            element=element,
            admin1=admin1,
            date=date + pd.DateOffset(months=2 if period == "QS" else 0, days=14),
            value=value
        ) for date, value in forecast_points.iteritems()]

    ForecastedDataPoint.objects.filter(element=element).delete()
    ForecastedDataPoint.objects.bulk_create(objs)

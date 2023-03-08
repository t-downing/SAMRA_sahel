import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.exponential_smoothing.ets import ETSModel
from statsmodels.tsa.api import ExponentialSmoothing
from statsmodels.tsa.forecasting.theta import ThetaModel

from ..models import Variable, Source, ForecastedDataPoint

# TODO: make this just trigger on data add, or somewhere else by admin
# TODO: make sure this forecasts up to modeling time (for very old data)


def forecast_element(element_pk, adm0, sarima_params=None):
    use_model = 'ETS'
    forecast_years = 2
    variable = Variable.objects.get(pk=element_pk)
    df = pd.DataFrame(variable.measureddatapoints.filter(admin0=adm0).values())

    if df.empty:
        print(f"no datapoints for {variable}, cannot forecast")
        return
    print(f"forecasting for {variable} now")

    # determine correct periodicity
    # TODO: deal with periodicity for non-seasonal data sources
    if variable.source_for_model is not None:
        df = df[df["source_id"] == variable.source_for_model.pk]
        number_of_periods = variable.source_for_model.number_of_periods
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
        message = ''
        if use_model == 'ExpSmo':
            model = ExponentialSmoothing(dff, trend="add", damped_trend=True)
            message = "used ExpSmo"
        elif use_model == 'ETS':
            try:
                model = ETSModel(dff, error="add", trend="add", damped_trend=True, seasonal="add", seasonal_periods=number_of_periods)
                message = f"used ETS"
            except:
                try:
                    if variable.unit == "1":
                        if len(dff) > number_of_periods - 1:
                            model = SARIMAX(dff, order=[0, 0, 0], seasonal_order=[0, 1, 0, number_of_periods])
                            message = f"used SARIMAX seasonal"
                        else:
                            model = SARIMAX(dff, order=[0, 1, 0], seasonal_order=[0, 0, 0, 0])
                            message = f"used SARIMAX non-seasonal (just trend)"
                    else:
                        model = ETSModel(dff, error="add", trend="add", damped_trend=True)
                        message = f"used ET damped"
                except:
                    try:
                        model = ETSModel(dff, error="add", trend="add")
                        message = f"used ET"
                    except:
                        model = ETSModel(dff, error="add")
                        message = f"used ET"
        elif use_model == 'Theta':
            model = ThetaModel(dff, period=number_of_periods)

        # if Source.objects.get(pk=df["source_id"].iloc[0]).pk == 7:
        #     if use_model == 'ExpSmo':
        #         model = ExponentialSmoothing(dff, trend="add", damped_trend=True, seasonal="add", seasonal_periods=number_of_periods, use_boxcox=True)
        #     elif use_model == 'ETS':
        #         model = SARIMAX(dff, order=[1, 1, number_of_periods + 1], seasonal_order=[1, 1, 0, number_of_periods])
        #     elif use_model == 'Theta':
        #         model = ThetaModel(dff, period=number_of_periods)
        fit = model.fit(disp=False)
        pred = fit.get_prediction(start=len(dff), end=len(dff)+forecast_periods-1)
        forecast_points = pred.summary_frame(alpha=0.05)
        # forecast_points = fit.forecast(steps=forecast_periods)
        forecast_points = forecast_points.rename_axis('date').reset_index()
        # print(forecast_points)
        print(message)

        dateoffset = pd.DateOffset(months=2 if period == "QS" else 0, days=14 if period in ["QS", "MS"] else 10)

        if 'pi_upper' not in forecast_points.columns:
            forecast_points = forecast_points.rename(columns={'mean_ci_upper': 'pi_upper', 'mean_ci_lower': 'pi_lower'})

        # record and re-shift forward to 15th of month
        objs += [
            ForecastedDataPoint(
                element=variable,
                admin0=adm0,
                admin1=admin1,
                date=row.date + dateoffset,
                value=row.mean,
                upper_bound=row.pi_upper,
                lower_bound=row.pi_lower,
            )
            for row in forecast_points.itertuples()
        ]

    ForecastedDataPoint.objects.filter(element=variable, admin0=adm0).delete()
    ForecastedDataPoint.objects.bulk_create(objs)

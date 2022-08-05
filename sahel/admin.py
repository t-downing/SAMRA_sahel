from django.contrib import admin
from . import models

admin.site.register(models.Element)
admin.site.register(models.SimulatedDataPoint)
admin.site.register(models.Connection)
admin.site.register(models.ElementGroup)
admin.site.register(models.Source)
admin.site.register(models.RegularDataset)
admin.site.register(models.MeasuredDataPoint)
admin.site.register(models.ResponseOption)
admin.site.register(models.ConstantValue)
admin.site.register(models.SeasonalInputDataPoint)
admin.site.register(models.ForecastedDataPoint)
admin.site.register(models.PulseValue)
admin.site.register(models.HouseholdConstantValue)
from django.contrib import admin
from . import models

admin.site.register(models.Element)
admin.site.register(models.SimulatedDataPoint)
admin.site.register(models.Connection)
from django.contrib import admin
from . import models
from import_export import resources
from import_export.admin import ImportExportModelAdmin


class ElementResource(resources.ModelResource):
    class Meta:
        model = models.Element


class ElementAdmin(ImportExportModelAdmin):
    resource_class = ElementResource


admin.site.register(models.Variable)
admin.site.register(models.SimulatedDataPoint)
admin.site.register(models.VariableConnection)
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
admin.site.register(models.Scenario)
admin.site.register(models.ScenarioConstantValue)
admin.site.register(models.Element, ElementAdmin)
admin.site.register(models.SituationalAnalysis)
admin.site.register(models.TheoryOfChange)
admin.site.register(models.ShockStructure)
admin.site.register(models.ElementConnection)
admin.site.register(models.Story)
admin.site.register(models.VariablePosition)
admin.site.register(models.SamraModel)
admin.site.register(models.EvidenceBit)
admin.site.register(models.Sector)
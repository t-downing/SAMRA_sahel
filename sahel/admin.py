from django.contrib import admin
from . import models
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from import_export.widgets import ManyToManyWidget

# RESOURCES
class ElementResource(resources.ModelResource):
    class Meta:
        model = models.Element


class ElementResourceAdmin(ImportExportModelAdmin):
    resource_class = ElementResource


class SituationalAnalysisResource(resources.ModelResource):
    evidencebits = Field(
        attribute="evidencebits",
        widget=ManyToManyWidget(model=models.EvidenceBit, separator="|", field="content")
    )

    class Meta:
        model = models.SituationalAnalysis


class SituationalAnalysisAdmin(ImportExportModelAdmin):
    resource_class = SituationalAnalysisResource

    list_filter = [
        "samramodel"
    ]


class VariableResource(resources.ModelResource):
    class Meta:
        model = models.Variable


class VariableAdmin(ImportExportModelAdmin):
    resource_class =  VariableResource

    list_filter = [
        'samramodel',
        'sd_type'
    ]


# REGISTRATION
admin.site.register(models.Variable, VariableAdmin)
admin.site.register(models.SimulatedDataPoint)
admin.site.register(models.VariableConnection)
admin.site.register(models.ElementGroup)
admin.site.register(models.Source)
admin.site.register(models.RegularDataset)
admin.site.register(models.MeasuredDataPoint)
admin.site.register(models.ResponseOption)
admin.site.register(models.ResponseConstantValue)
admin.site.register(models.SeasonalInputDataPoint)
admin.site.register(models.ForecastedDataPoint)
admin.site.register(models.PulseValue)
admin.site.register(models.HouseholdConstantValue)
admin.site.register(models.Scenario)
admin.site.register(models.ScenarioConstantValue)
admin.site.register(models.Element, ElementResourceAdmin)
admin.site.register(models.SituationalAnalysis, SituationalAnalysisAdmin)
admin.site.register(models.TheoryOfChange)
admin.site.register(models.ShockStructure)
admin.site.register(models.ElementConnection)
admin.site.register(models.Story)
admin.site.register(models.VariablePosition)
admin.site.register(models.SamraModel)
admin.site.register(models.EvidenceBit)
admin.site.register(models.Sector)
admin.site.register(models.Region)
admin.site.register(models.SAField)
admin.site.register(models.SAFieldOption)
admin.site.register(models.SAFieldValue)
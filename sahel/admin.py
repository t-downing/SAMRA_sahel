from django.contrib import admin
from . import models
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.fields import Field
from import_export.widgets import ManyToManyWidget

admin.site.site_header = "SAMRA administration"
admin.site.site_title = "SAMRA site admin"


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
    resource_class = VariableResource
    list_filter = [
        'samramodel',
        'sd_type'
    ]
    list_display = ('__str__', 'sd_type', 'date_created', )


class MeasuredDataPointResource(resources.ModelResource):
    class Meta:
        model = models.MeasuredDataPoint


class MeasuredDataPointAdmin(ImportExportModelAdmin):
    resource_class = MeasuredDataPointResource
    list_filter = [
        'element',
        'admin0',
        'admin1',
        'admin2',
    ]


class ResponseConstantResource(resources.ModelResource):
    class Meta:
        model = models.ResponseConstantValue


class ResponseConstantAdmin(ImportExportModelAdmin):
    resource_class = ResponseConstantResource
    list_filter = [
        'element',
        'admin0',
        'responseoption'
    ]


class HouseholdConstantResource(resources.ModelResource):
    class Meta:
        model = models.HouseholdConstantValue


class HouseholdConstantAdmin(ImportExportModelAdmin):
    resource_class = HouseholdConstantResource
    list_filter = [
        'element',
        'admin0',
    ]


class ScenarioConstantResource(resources.ModelResource):
    class Meta:
        model = models.ScenarioConstantValue


class ScenarioConstantAdmin(ImportExportModelAdmin):
    resource_class = ScenarioConstantResource
    list_filter = [
        'element',
        'scenario',
    ]


class ResponsePulseResource(resources.ModelResource):
    class Meta:
        model = models.PulseValue


class ResponsePulseAdmin(ImportExportModelAdmin):
    resource_class = ResponsePulseResource
    list_filter = [
        'element',
        'responseoption',
        'admin0',
    ]


class SeasonalInputResource(resources.ModelResource):
    class Meta:
        model = models.SeasonalInputDataPoint


class SeasonalInputAdmin(ImportExportModelAdmin):
    resource_class = SeasonalInputResource
    list_filter = [
        'element',
        'admin0',
    ]


# REGISTRATION
admin.site.register(models.Variable, VariableAdmin)
admin.site.register(models.SimulatedDataPoint)
admin.site.register(models.VariableConnection)
admin.site.register(models.ElementGroup)
admin.site.register(models.Source)
admin.site.register(models.RegularDataset)
admin.site.register(models.MeasuredDataPoint, MeasuredDataPointAdmin)
admin.site.register(models.ResponseOption)
admin.site.register(models.ResponseConstantValue, ResponseConstantAdmin)
admin.site.register(models.SeasonalInputDataPoint, SeasonalInputAdmin)
admin.site.register(models.ForecastedDataPoint)
admin.site.register(models.PulseValue, ResponsePulseAdmin)
admin.site.register(models.HouseholdConstantValue, HouseholdConstantAdmin)
admin.site.register(models.Scenario)
admin.site.register(models.ScenarioConstantValue, ScenarioConstantAdmin)
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
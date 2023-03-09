from django.db import models
from model_utils.managers import InheritanceManager
from colorfield.fields import ColorField
import datetime

# TODO: refactor element to variable
# TODO: add admin0-2 as models


ADMIN0S = ['Mali', 'Mauritanie']
CURRENCY = {
    'Mali': 'FCFA',
    'Mauritanie': 'MRU'
}


class SamraModel(models.Model):
    name = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    default_story = models.OneToOneField("story", on_delete=models.SET_NULL, null=True, related_name="defaultfor")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "SAMRA model"


class Node(models.Model):
    label = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    samramodel = models.ForeignKey("samramodel", on_delete=models.SET_NULL, null=True)

    class Meta:
        abstract = True
        ordering = ["label"]

    def __str__(self):
        return f"{self.label}; pk: {self.pk}"


class Sector(models.Model):
    name = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    samramodel = models.ForeignKey("samramodel", on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name


class Element(Node):
    FORMAL_SECTOR = "FS"
    INFORMAL_SECTOR = "IS"
    BOTH_SECTOR = "BS"
    SECTOR_TYPES = (
        (FORMAL_SECTOR, "Formal"),
        (INFORMAL_SECTOR, "Informal"),
        (BOTH_SECTOR, "Both"),
    )
    objects = InheritanceManager()
    element_group = models.ForeignKey("elementgroup", related_name="elements", null=True, blank=True,
                                      on_delete=models.SET_NULL)
    # element_group_integer = models.IntegerField(null=True, blank=True)
    x_pos = models.FloatField(null=True, blank=True)
    y_pos = models.FloatField(null=True, blank=True)
    sectors = models.ManyToManyField("sector", blank=True, related_name="elements")
    sector_type = models.CharField(choices=SECTOR_TYPES, max_length=2, null=True, blank=True)
    regions = models.ManyToManyField("region", blank=True, related_name="elements")
    source = models.ForeignKey("source", blank=True, null=True, related_name="elements", on_delete=models.SET_NULL)
    # stories = models.ManyToManyField("story", related_name="elements", blank=True)
    kumu_id = models.CharField(max_length=100, null=True, blank=True)


class Region(models.Model):
    name = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    samramodel = models.ForeignKey("samramodel", on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name


class SituationalAnalysis(Element):
    # for now, SA_FIELDS must match names of fields to be edited in map
    SA_FIELDS = ["status", "trend", "resilience_vulnerability"]

    SITUATIONAL_ANALYSIS = "SA"
    SA_TYPES = (
        (SITUATIONAL_ANALYSIS, "Situational Analysis"),
    )

    SA_STATUS_GOOD = "AA"
    SA_STATUS_OK = "BB"
    SA_STATUS_BAD = "CC"
    SA_STATUSES = (
        (SA_STATUS_GOOD, "Good"),
        (SA_STATUS_OK, "Medium"),
        (SA_STATUS_BAD, "Bad"),
    )

    SA_TREND_IMPROVING = "AA"
    SA_TREND_STAGNANT = "BB"
    SA_TREND_WORSENING = "CC"
    SA_TRENDS = (
        (SA_TREND_IMPROVING, "Improving"),
        (SA_TREND_STAGNANT, "Stagnant"),
        (SA_TREND_WORSENING, "Worsening"),
    )

    SA_RES_HIGH = "AA"
    SA_RES_MED = "BB"
    SA_RES_LOW = "CC"
    SA_RESILIENCE_OPTIONS = (
        (SA_RES_HIGH, "Resilience"),
        (SA_RES_MED, "Resilience and Vulnerability"),
        (SA_RES_LOW, "Vulnerability"),
    )

    element_type = models.CharField(choices=SA_TYPES, max_length=2, default=SITUATIONAL_ANALYSIS)
    status = models.CharField(choices=SA_STATUSES, max_length=2, null=True, blank=True)
    trend = models.CharField(choices=SA_TRENDS, max_length=2, null=True, blank=True)
    resilience_vulnerability = models.CharField("resilience/vulnerability", choices=SA_RESILIENCE_OPTIONS, max_length=2, null=True, blank=True)

    class Meta:
        verbose_name = "situational analysis"


class SAField(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class SAFieldOption(models.Model):
    label = models.CharField(max_length=100)
    safield = models.ForeignKey("safield", related_name="safieldoptions", on_delete=models.CASCADE)
    color = ColorField(default="grey")
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.safield.name}: {self.label}"


class SAFieldValue(models.Model):
    sa = models.ForeignKey("situationalanalysis", on_delete=models.CASCADE, related_name="safieldvalues")
    safieldoption = models.ForeignKey("safieldoption", on_delete=models.CASCADE, related_name="safieldvalues")
    date = models.DateField(default=datetime.date.today)

    def __str__(self):
        return f"{self.sa.label}; {self.safieldoption.safield.name}: {self.safieldoption}; {self.date}"


class TheoryOfChange(Element):
    INTERVENTION = "IV"
    INTERVENTION_CLUSTER = "IC"
    SUB_OUTCOME = "SO"
    PRIMARY_OUTCOME = "PO"
    SECTOR_GOAL = "SG"
    PROGRAMME_GOAL = "PG"
    TOC_TYPES = (
        (INTERVENTION, "Intervention"),
        (INTERVENTION_CLUSTER, "Intervention Cluster"),
        (SUB_OUTCOME, "Sub-Outcome"),
        (PRIMARY_OUTCOME, "Primary Outcome"),
        (SECTOR_GOAL, "Sector Goal"),
        (PROGRAMME_GOAL, "Programme Goal"),
    )
    element_type = models.CharField(choices=TOC_TYPES, max_length=2, default=INTERVENTION)

    class Meta:
        verbose_name = "theory of change"


class ShockStructure(Element):
    SHOCK_EFFECT = "SE"
    SHOCK = "SH"
    SHOCKSTRUCTURE_TYPES = (
        (SHOCK_EFFECT, "shock effect"),
        (SHOCK, "shock"),
    )
    element_type = models.CharField(choices=SHOCKSTRUCTURE_TYPES, max_length=2, default=SHOCK_EFFECT)

    class Meta:
        verbose_name = "shock structure"


class Story(models.Model):
    name = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    samramodel = models.ForeignKey("samramodel", null=True, on_delete=models.SET_NULL, related_name="stories")

    elements = models.ManyToManyField("element", related_name="stories", blank=True)

    def __str__(self):
        return self.name


# TODO: do types properly
# TODO: make units their own model so all this isn't hardcoded
class Variable(Node):
    STOCK = 'Stock'
    FLOW = 'Flow'
    VARIABLE = 'Variable'
    INPUT = 'Input'
    RESPONSE_CONSTANT = 'Constant'
    SEASONAL_INPUT = 'Seasonal Input'
    RESPONSE_PULSE = 'Pulse Input'
    HOUSEHOLD_CONSTANT = 'Household Constant'
    SCENARIO_CONSTANT = 'Scenario Constant'
    GEOGRAPHIC_CONSTANT = 'Geographic Constant'
    SD_TYPES = (
        (STOCK, "Stock"),
        (FLOW, "Flow"),
        (VARIABLE, "Variable"),
        (INPUT, "Input"),
        (RESPONSE_CONSTANT, "Constant"),
        (SEASONAL_INPUT, "Entrée Saisonnière"),
        (RESPONSE_PULSE, "Entrée Impulsion"),
        (HOUSEHOLD_CONSTANT, "Qualité Ménage"),
        (SCENARIO_CONSTANT, "Variation Scénario"),
        (GEOGRAPHIC_CONSTANT, 'Constant Géographique')
    )
    CONSTANTS = [RESPONSE_CONSTANT, HOUSEHOLD_CONSTANT, SCENARIO_CONSTANT, GEOGRAPHIC_CONSTANT]
    UNIT_OPTIONS = (
        ("tête", "tête"),
        ("tête / mois", "tête / mois"),
        ("tête / an", "tête / an"),
        ("LCY", "LCY"),
        ("LCY / mois", "LCY / mois"),
        ("LCY / jour", "LCY / jour"),
        ("LCY / an", "LCY / an"),
        ("LCY / tête", "LCY / tête"),
        ("LCY / kg", "LCY / kg"),
        ("LCY / L", "LCY / L"),
        ("LCY / personne / mois", "LCY / personne / mois"),
        ("kg", "kg"),
        ("kg / mois", "kg / mois"),
        ("kg / jour", "kg / jour"),
        ("kg / tête / mois", "kg / tête / mois"),
        ("L", "L"),
        ("L / mois", "L / mois"),
        ("L / jour", "L / jour"),
        ("kcal", "kcal"),
        ("kcal / jour", "kcal / jour"),
        ("1", "1"),
        ("personne", "personne"),
        ("kcal / personne / jour", "kcal / personne / jour"),
        ("1 / mois", "1 / mois"),
        ("1 / an", "1 / an"),
        ("mm / jour", "mm / jour"),
        ("NDVI", "NDVI"),
        ("USD / tonne", "USD / tonne"),
        ('kg / hec', 'kg / hec'),
        ('hec', 'hec'),
    )
    AGG_OPTIONS = (
        ("MEAN", "moyen"),
        ("SUM", "total"),
        ("CHANGE", "change"),
        ("%CHANGE", "% change"),
    )
    element = models.ForeignKey("element", related_name="variables", null=True, blank=True, on_delete=models.SET_NULL)
    x_pos = models.FloatField(null=True, blank=True)
    y_pos = models.FloatField(null=True, blank=True)
    equation = models.CharField(max_length=500, null=True, blank=True)
    sim_input_var = models.BooleanField(default=False)
    unit = models.CharField(max_length=100, null=True, choices=UNIT_OPTIONS)
    sd_type = models.CharField(max_length=100, choices=SD_TYPES, null=True)
    sd_source = models.ForeignKey(
        "self", related_name="outflows", null=True, blank=True, on_delete=models.SET_NULL,
        limit_choices_to={'sd_type': STOCK}
    )
    sd_sink = models.ForeignKey(
        "self", related_name="inflows", null=True, blank=True, on_delete=models.SET_NULL,
        limit_choices_to={'sd_type': STOCK}
    )
    vam_commodity = models.CharField(max_length=200, null=True, blank=True)
    mid_threshold = models.FloatField(null=True, blank=True)
    high_threshold = models.FloatField(null=True, blank=True)
    high_is_bad = models.BooleanField(default=False)
    constant_default_value = models.FloatField(null=True, blank=True, default=0.0)
    aggregate_by = models.CharField(max_length=200, choices=AGG_OPTIONS, default="MEAN")
    dm_globalform_fieldgroup = models.CharField(max_length=200, null=True, blank=True)
    dm_globalform_group_highfield = models.CharField(max_length=200, null=True, blank=True)
    dm_globalform_group_midfield = models.CharField(max_length=200, null=True, blank=True)
    dm_globalform_group_lowfield = models.CharField(max_length=200, null=True, blank=True)
    dm_globalform_field = models.CharField(max_length=200, null=True, blank=True)
    dm_globalform_field_highvalue = models.CharField(max_length=200, null=True, blank=True)
    dm_globalform_field_midvalue = models.CharField(max_length=200, null=True, blank=True)
    dm_globalform_field_lowvalue = models.CharField(max_length=200, null=True, blank=True)
    source_for_model = models.ForeignKey(
        "source", related_name="model_element_uses", null=True, blank=True, on_delete=models.SET_NULL
    )
    kcal_per_kg = models.IntegerField(null=True, blank=True)
    model_output_variable = models.BooleanField(default=True)
    stock_initial_value = models.FloatField(null=True, blank=True)
    mrt_prixmarche_name = models.CharField(max_length=200, null=True, blank=True)
    must_be_positive = models.BooleanField(default=True)
    stock_initial_value_variable = models.OneToOneField(
        'self', related_name='stock', null=True, blank=True, on_delete=models.SET_NULL,
        limit_choices_to={'sd_type__in': CONSTANTS},
    )


class VariablePosition(models.Model):
    variable = models.ForeignKey("variable", on_delete=models.CASCADE, related_name="variablepositions")
    story = models.ForeignKey("story", on_delete=models.CASCADE, related_name="variablepositions")
    x_pos = models.FloatField()
    y_pos = models.FloatField()

    def __str__(self):
        return f"{self.variable=}, {self.story=}, {self.x_pos=}, {self.y_pos=}"

    class Meta:
        unique_together = ("variable", "story")


class ElementPosition(models.Model):
    element = models.ForeignKey("element", on_delete=models.CASCADE, related_name="elementpositions")
    story = models.ForeignKey("story", on_delete=models.CASCADE, related_name="elementpositions")
    x_pos = models.FloatField()
    y_pos = models.FloatField()

    def __str__(self):
        return f"{self.element=}, {self.story=}, {self.x_pos=}, {self.y_pos=}"

    class Meta:
        unique_together = ("element", "story")


class VariableConnection(models.Model):
    from_variable = models.ForeignKey("variable", related_name="downstream_connections", on_delete=models.CASCADE)
    to_variable = models.ForeignKey("variable", related_name="upstream_connections", on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_variable} to {self.to_variable}"

    class Meta:
        ordering = ["-date_created"]
        unique_together = ("from_variable", "to_variable")


class ElementConnection(models.Model):
    from_element = models.ForeignKey("element", related_name="downstream_connections", on_delete=models.CASCADE)
    to_element = models.ForeignKey("element", related_name="upstream_connections", on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.from_element} to {self.to_element}"

    class Meta:
        ordering = ["-date_created"]
        unique_together = ("from_element", "to_element")


class ElementGroup(Node):
    class Meta:
        ordering = ["-date_created"]


class Source(models.Model):
    title = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    number_of_periods = models.IntegerField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)
    samramodels = models.ManyToManyField("samramodel", related_name="sources")
    date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.title}; pk: {self.pk}"

    class Meta:
        ordering = ["-date_created"]


class EvidenceBit(models.Model):
    content = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    eb_date = models.DateField(null=True, blank=True)
    source = models.ForeignKey("source", on_delete=models.SET_NULL, related_name="evidencebits", null=True)
    elements = models.ManyToManyField("element", blank=True, related_name="evidencebits")
    elementconnections = models.ManyToManyField("elementconnection", blank=True, related_name="evidencebits")

    def __str__(self):
        return self.content


class RegularDataset(models.Model):
    source = models.OneToOneField("source", related_name="regulardataset", on_delete=models.CASCADE)
    last_updated_date = models.DateTimeField()
    hdx_identifier = models.CharField(max_length=200, null=True, blank=True)
    hdx_resource_number = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.source} RegularDataset"


class MeasuredDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField(null=True)
    element = models.ForeignKey(
        "variable", related_name="measureddatapoints", on_delete=models.CASCADE,
        limit_choices_to={'sd_type': Variable.INPUT},
    )
    source = models.ForeignKey("source", related_name="measureddatapoints", null=True, on_delete=models.SET_NULL)
    admin0 = models.CharField(max_length=200, null=True, blank=True)
    admin1 = models.CharField(max_length=200, null=True, blank=True)
    admin2 = models.CharField(max_length=200, null=True, blank=True)
    market = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(self.value)


class SimulatedDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField(null=True)
    element = models.ForeignKey("variable", related_name="simulateddatapoints", on_delete=models.CASCADE)
    scenario = models.ForeignKey("scenario", related_name="simulateddatapoints", null=True, on_delete=models.CASCADE)
    responseoption = models.ForeignKey("responseoption", related_name="simulateddatapoints", null=True, on_delete=models.CASCADE)
    admin0 = models.CharField(max_length=200, null=True, blank=True)
    admin1 = models.CharField(max_length=200, null=True, blank=True)
    admin2 = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(f"Element: {self.element}; Date: {self.date}; Simulated Value: {self.value}")


class ForecastedDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField()
    element = models.ForeignKey("variable", related_name="forecasteddatapoints", on_delete=models.CASCADE)
    admin0 = models.CharField(max_length=200, null=True, blank=True)
    admin1 = models.CharField(max_length=200, null=True, blank=True)
    admin2 = models.CharField(max_length=200, null=True, blank=True)
    upper_bound = models.FloatField(null=True, blank=True)
    lower_bound = models.FloatField(null=True, blank=True)

    def __str__(self):
        return str(f"Element: {self.element}; Date: {self.date}; Forecasted Value: {self.value}")


class SeasonalInputDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField()
    admin0 = models.CharField(max_length=200, null=True, blank=True)
    admin1 = models.CharField(max_length=200, null=True, blank=True)
    admin2 = models.CharField(max_length=200, null=True, blank=True)
    element = models.ForeignKey(
        "variable", related_name="seasonalinputdatapoints", on_delete=models.CASCADE,
        limit_choices_to={'sd_type': Variable.SEASONAL_INPUT}
    )

    def __str__(self):
        return f"Element: {self.element}; Date: {self.date}; Seasonal Value: {self.value}"


class ResponseOption(models.Model):
    name = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    samramodel = models.ForeignKey("samramodel", related_name="responseoptions", on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name


class Scenario(models.Model):
    name = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    samramodel = models.ForeignKey("samramodel", related_name="scenarios", on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name


class ResponseConstantValue(models.Model):
    element = models.ForeignKey(
        "variable", related_name="responseconstantvalues", on_delete=models.CASCADE,
        limit_choices_to={'sd_type': Variable.RESPONSE_CONSTANT}
    )
    responseoption = models.ForeignKey("responseoption", related_name="responseconstantvalues", on_delete=models.CASCADE)
    admin0 = models.CharField(max_length=200, null=True, blank=True)
    value = models.FloatField()

    def __str__(self):
        return f"Element: {self.element}; ResponseOption: {self.responseoption}; Value: {self.value}"


class ScenarioConstantValue(models.Model):
    element = models.ForeignKey(
        "variable", related_name="scenarioconstantvalues", on_delete=models.CASCADE,
        limit_choices_to={'sd_type': Variable.SCENARIO_CONSTANT}
    )
    scenario = models.ForeignKey("scenario", related_name="scenarioconstantvalues", on_delete=models.CASCADE)
    value = models.FloatField()

    def __str__(self):
        return f"Element: {self.element}; Scenario: {self.scenario}; Value: {self.value}"


class HouseholdConstantValue(models.Model):
    element = models.ForeignKey(
        "variable", related_name="householdconstantvalues", on_delete=models.CASCADE,
        limit_choices_to={'sd_type': Variable.HOUSEHOLD_CONSTANT}
    )
    value = models.FloatField(null=True)
    admin0 = models.CharField(max_length=200, null=True, blank=True)
    admin1 = models.CharField(max_length=200, null=True, blank=True)
    admin2 = models.CharField(max_length=200, null=True, blank=True)
    source = models.ForeignKey("source", related_name="householdconstantvalues", null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Element: {self.element}; Value: {self.value}"


class PulseValue(models.Model):
    element = models.ForeignKey(
        "variable", related_name="pulsevalues", on_delete=models.CASCADE,
        limit_choices_to={'sd_type': Variable.RESPONSE_PULSE}
    )
    responseoption = models.ForeignKey("responseoption", related_name="pulsevalues", on_delete=models.CASCADE)
    admin0 = models.CharField(max_length=200, null=True, blank=True)
    value = models.FloatField()
    startdate = models.DateField()
    enddate = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Element: {self.element}; ResponseOption: {self.responseoption}; Pulse Height: {self.value}"


# NOTE: still not used, just using HH values for now
class GeographicConstantValue(models.Model):
    element = models.ForeignKey(
        'variable', related_name='countryconstantvalues', on_delete=models.CASCADE,
        limit_choices_to={'sd_type': Variable.GEOGRAPHIC_CONSTANT}
    )
    value = models.FloatField(null=True)
    admin0 = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"Element: {self.element}; Country: {self.admin0}; Value: {self.value}"

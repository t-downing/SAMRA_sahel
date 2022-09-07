from django.db import models


class Element(models.Model):
    SD_TYPES = (
        ("Stock", "Stock"),
        ("Flow", "Flow"),
        ("Variable", "Variable"),
        ("Input", "Input"),
        ("Constant", "Constant"),
        ("Seasonal Input", "Entrée Saisonnière"),
        ("Pulse Input", "Entrée Impulsion"),
        ("Household Constant", "Qualité Ménage"),
        ("Scenario Constant", "Variation Scénario"),
    )
    UNIT_OPTIONS = (
        ("tête", "tête"),
        ("tête / mois", "tête / mois"),
        ("tête / an", "tête / an"),
        ("FCFA", "FCFA"),
        ("FCFA / mois", "FCFA / mois"),
        ("FCFA / jour", "FCFA / jour"),
        ("FCFA / an", "FCFA / an"),
        ("FCFA / tête", "FCFA / tête"),
        ("FCFA / kg", "FCFA / kg"),
        ("FCFA / L", "FCFA / L"),
        ("kg", "kg"),
        ("kg / mois", "kg / mois"),
        ("kg / jour", "kg / jour"),
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
    )
    AGG_OPTIONS = (
        ("MEAN", "moyen"),
        ("SUM", "total"),
        ("CHANGE", "change"),
        ("%CHANGE", "% change"),
    )
    label = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    x_pos = models.FloatField(null=True, blank=True)
    y_pos = models.FloatField(null=True, blank=True)
    equation = models.CharField(max_length=500, null=True, blank=True)
    sim_input_var = models.BooleanField(default=False)
    unit = models.CharField(max_length=100, null=True, blank=True, choices=UNIT_OPTIONS)
    sd_type = models.CharField(max_length=100, choices=SD_TYPES, null=True, blank=True)
    sd_source = models.ForeignKey("self", related_name="outflows", null=True, blank=True, on_delete=models.SET_NULL)
    sd_sink = models.ForeignKey("self", related_name="inflows", null=True, blank=True, on_delete=models.SET_NULL)
    element_group = models.ForeignKey("elementgroup", related_name="elements", null=True, blank=True,
                                      on_delete=models.SET_NULL)
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
    source_for_model = models.ForeignKey("source", related_name="model_element_uses", null=True, blank=True, on_delete=models.SET_NULL)
    kcal_per_kg = models.IntegerField(null=True, blank=True)
    model_output_variable = models.BooleanField(default=True)
    stock_initial_value = models.FloatField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.label}; pk: {self.pk}"

    class Meta:
        ordering = ["-date_created"]


class Connection(models.Model):
    from_element = models.ForeignKey("element", related_name="downstream_connections", on_delete=models.CASCADE)
    to_element = models.ForeignKey("element", related_name="upstream_connections", on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.from_element} to {self.to_element}"

    class Meta:
        ordering = ["-date_created"]
        unique_together = ("from_element", "to_element")


class ElementGroup(models.Model):
    label = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ["-date_created"]


class Source(models.Model):
    title = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    number_of_periods = models.IntegerField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.title}; pk: {self.pk}"

    class Meta:
        ordering = ["-date_created"]


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
    element = models.ForeignKey("element", related_name="measureddatapoints", on_delete=models.CASCADE)
    source = models.ForeignKey("source", related_name="measureddatapoints", null=True, on_delete=models.SET_NULL)
    admin1 = models.CharField(max_length=200, null=True, blank=True)
    admin2 = models.CharField(max_length=200, null=True, blank=True)
    market = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(self.value)


class SimulatedDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField(null=True)
    element = models.ForeignKey("element", related_name="simulateddatapoints", on_delete=models.CASCADE)
    scenario = models.ForeignKey("scenario", related_name="simulateddatapoints", null=True, on_delete=models.CASCADE)
    responseoption = models.ForeignKey("responseoption", related_name="simulateddatapoints", null=True, on_delete=models.CASCADE)
    admin1 = models.CharField(max_length=200, null=True, blank=True)
    admin2 = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(f"Element: {self.element}; Date: {self.date}; Simulated Value: {self.value}")


class ForecastedDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField()
    element = models.ForeignKey("element", related_name="forecasteddatapoints", on_delete=models.CASCADE)
    admin1 = models.CharField(max_length=200, null=True, blank=True)
    admin2 = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(f"Element: {self.element}; Date: {self.date}; Forecasted Value: {self.value}")


class SeasonalInputDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField()
    element = models.ForeignKey("element", related_name="seasonalinputdatapoints", on_delete=models.CASCADE)

    def __str__(self):
        return f"Element: {self.element}; Date: {self.date}; Seasonal Value: {self.value}"


class ResponseOption(models.Model):
    name = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Scenario(models.Model):
    name = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class ConstantValue(models.Model):
    element = models.ForeignKey("element", related_name="constantvalues", on_delete=models.CASCADE)
    responseoption = models.ForeignKey("responseoption", related_name="constantvalues", on_delete=models.CASCADE)
    value = models.FloatField()

    def __str__(self):
        return f"Element: {self.element}; ResponseOption: {self.responseoption}; Value: {self.value}"


class ScenarioConstantValue(models.Model):
    element = models.ForeignKey("element", related_name="scenarioconstantvalues", on_delete=models.CASCADE)
    scenario = models.ForeignKey("scenario", related_name="scenarioconstantvalues", on_delete=models.CASCADE)
    value = models.FloatField()

    def __str__(self):
        return f"Element: {self.element}; Scenario: {self.scenario}; Value: {self.value}"


class HouseholdConstantValue(models.Model):
    element = models.ForeignKey("element", related_name="householdconstantvalues", on_delete=models.CASCADE)
    value = models.FloatField(null=True)

    def __str__(self):
        return f"Element: {self.element}; Value: {self.value}"


class PulseValue(models.Model):
    element = models.ForeignKey("element", related_name="pulsevalues", on_delete=models.CASCADE)
    responseoption = models.ForeignKey("responseoption", related_name="pulsevalues", on_delete=models.CASCADE)
    value = models.FloatField()
    startdate = models.DateField()
    enddate = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Element: {self.element}; ResponseOption: {self.responseoption}; Pulse Height: {self.value}"


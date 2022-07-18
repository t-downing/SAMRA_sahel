from django.db import models


SYSTEM_DYNAMICS_TYPES = (
    ("Stock", "Stock"),
    ("Flow", "Flow"),
    ("Variable", "Variable")
)


class Element(models.Model):
    label = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    x_pos = models.FloatField(null=True, blank=True)
    y_pos = models.FloatField(null=True, blank=True)
    equation = models.CharField(max_length=500, null=True, blank=True)
    sim_input_var = models.BooleanField(default=False)
    unit = models.CharField(max_length=100, null=True, blank=True)
    sd_type = models.CharField(max_length=100, choices=SYSTEM_DYNAMICS_TYPES, null=True, blank=True)
    sd_source = models.ForeignKey("self", related_name="outflows", null=True, blank=True, on_delete=models.SET_NULL)
    sd_sink = models.ForeignKey("self", related_name="inflows", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.label

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


class MeasuredDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField()
    element = models.ForeignKey("element", related_name="measureddatapoints", on_delete=models.CASCADE)

    def __str__(self):
        return str(self.value)


class SimulatedDataPoint(models.Model):
    date = models.DateField()
    value = models.FloatField()
    element = models.ForeignKey("element", related_name="simulationdatapoints", on_delete=models.CASCADE)
    scenario = models.CharField(max_length=200)

    def __str__(self):
        return str(self.value)
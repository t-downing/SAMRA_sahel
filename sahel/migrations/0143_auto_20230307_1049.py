# Generated by Django 3.2.15 on 2023-03-07 10:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0142_householdconstantvalue_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='householdconstantvalue',
            name='admin1',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='householdconstantvalue',
            name='admin2',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]

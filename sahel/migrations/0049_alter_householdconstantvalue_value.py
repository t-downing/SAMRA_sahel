# Generated by Django 3.2.14 on 2022-08-04 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0048_alter_element_sd_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='householdconstantvalue',
            name='value',
            field=models.FloatField(null=True),
        ),
    ]

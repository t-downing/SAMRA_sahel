# Generated by Django 3.2.14 on 2022-09-01 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0063_rename_output_variables_element_model_output_variable'),
    ]

    operations = [
        migrations.AddField(
            model_name='element',
            name='stock_initial_value',
            field=models.FloatField(blank=True, null=True),
        ),
    ]

# Generated by Django 3.2.14 on 2022-07-15 08:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0004_simulationdatapoint_scenario'),
    ]

    operations = [
        migrations.AddField(
            model_name='element',
            name='sim_input_var',
            field=models.BooleanField(default=False),
        ),
    ]

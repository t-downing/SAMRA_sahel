# Generated by Django 3.2.14 on 2022-08-14 11:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0056_simulateddatapoint_scenario'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='simulateddatapoint',
            name='old_scenario',
        ),
    ]

# Generated by Django 3.2.14 on 2022-08-04 18:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0045_alter_element_unit'),
    ]

    operations = [
        migrations.CreateModel(
            name='HouseholdConstantValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField()),
                ('element', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='householdconstantvalues', to='sahel.element')),
            ],
        ),
    ]

# Generated by Django 3.2.14 on 2022-09-06 16:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0064_element_stock_initial_value'),
    ]

    operations = [
        migrations.AlterField(
            model_name='element',
            name='aggregate_by',
            field=models.CharField(choices=[('MEAN', 'moyen'), ('SUM', 'total'), ('CHANGE', 'change'), ('%CHANGE', '% change')], default='MEAN', max_length=200),
        ),
    ]

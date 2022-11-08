# Generated by Django 3.2.14 on 2022-07-28 07:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0032_alter_simulateddatapoint_element'),
    ]

    operations = [
        migrations.AlterField(
            model_name='element',
            name='sd_type',
            field=models.CharField(blank=True, choices=[('Stock', 'Stock'), ('Flow', 'Flow'), ('Variable', 'Variable'), ('Input', 'Input'), ('Constant', 'Constant'), ('Seasonal Input', 'Entrée Saisonnière')], max_length=100, null=True),
        ),
    ]

# Generated by Django 3.2.14 on 2022-09-14 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0079_remove_element_element_group_integer'),
    ]

    operations = [
        migrations.AddField(
            model_name='theoryofchange',
            name='toc_type',
            field=models.CharField(choices=[('IV', 'Intervention'), ('IC', "Groupe d'interventions"), ('SO', 'Sous-résultat'), ('PO', 'Résultat primaire'), ('SG', 'But du secteur'), ('PG', 'But du programme')], default='IV', max_length=2),
        ),
    ]

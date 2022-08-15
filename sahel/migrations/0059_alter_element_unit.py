# Generated by Django 3.2.14 on 2022-08-15 10:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0058_alter_element_unit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='element',
            name='unit',
            field=models.CharField(blank=True, choices=[('tête', 'tête'), ('tête / mois', 'tête / mois'), ('tête / an', 'tête / an'), ('FCFA', 'FCFA'), ('FCFA / mois', 'FCFA / mois'), ('FCFA / jour', 'FCFA / jour'), ('FCFA / an', 'FCFA / an'), ('FCFA / tête', 'FCFA / tête'), ('FCFA / kg', 'FCFA / kg'), ('FCFA / L', 'FCFA / L'), ('kg', 'kg'), ('kg / mois', 'kg / mois'), ('kg / jour', 'kg / jour'), ('L', 'L'), ('L / mois', 'L / mois'), ('L / jour', 'L / jour'), ('kcal', 'kcal'), ('kcal / jour', 'kcal / jour'), ('1', '1'), ('personne', 'personne'), ('kcal / personne / jour', 'kcal / personne / jour'), ('1 / mois', '1 / mois'), ('1 / an', '1 / an'), ('mm / jour', 'mm / jour'), ('NDVI', 'NDVI')], max_length=100, null=True),
        ),
    ]

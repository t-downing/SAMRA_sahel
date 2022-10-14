# Generated by Django 3.2.15 on 2022-10-13 14:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0112_alter_variableposition_unique_together'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='shockstructure',
            options={'verbose_name': 'shock structure'},
        ),
        migrations.AlterModelOptions(
            name='situationalanalysis',
            options={'verbose_name': 'situational analysis'},
        ),
        migrations.AlterModelOptions(
            name='theoryofchange',
            options={'verbose_name': 'theory of change'},
        ),
        migrations.AddField(
            model_name='evidencebit',
            name='elementconnections',
            field=models.ManyToManyField(blank=True, related_name='evidencebits', to='sahel.ElementConnection'),
        ),
        migrations.AlterField(
            model_name='shockstructure',
            name='element_type',
            field=models.CharField(choices=[('SE', 'shock effect'), ('SH', 'shock')], default='SE', max_length=2),
        ),
    ]

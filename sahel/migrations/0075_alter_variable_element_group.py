# Generated by Django 3.2.14 on 2022-09-14 13:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0074_alter_situationalanalysis_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='variable',
            name='element_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='variables', to='sahel.elementgroup'),
        ),
    ]

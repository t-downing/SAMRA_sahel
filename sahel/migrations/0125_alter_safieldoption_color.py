# Generated by Django 3.2.15 on 2022-11-09 09:35

import colorfield.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0124_auto_20221014_2029'),
    ]

    operations = [
        migrations.AlterField(
            model_name='safieldoption',
            name='color',
            field=colorfield.fields.ColorField(default='grey', image_field=None, max_length=18, samples=None),
        ),
    ]

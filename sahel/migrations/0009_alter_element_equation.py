# Generated by Django 3.2.14 on 2022-07-15 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0008_element_sd_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='element',
            name='equation',
            field=models.CharField(default='0', max_length=500),
        ),
    ]

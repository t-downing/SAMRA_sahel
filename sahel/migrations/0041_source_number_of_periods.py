# Generated by Django 3.2.14 on 2022-08-02 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0040_auto_20220802_1144'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='number_of_periods',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]

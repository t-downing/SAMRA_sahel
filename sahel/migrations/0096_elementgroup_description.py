# Generated by Django 3.2.15 on 2022-09-28 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0095_samramodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='elementgroup',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]

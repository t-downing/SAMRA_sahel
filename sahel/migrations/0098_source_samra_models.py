# Generated by Django 3.2.15 on 2022-09-28 18:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0097_auto_20220928_1849'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='samra_models',
            field=models.ManyToManyField(related_name='sources', to='sahel.SamraModel'),
        ),
    ]

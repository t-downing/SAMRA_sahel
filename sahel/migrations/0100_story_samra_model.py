# Generated by Django 3.2.15 on 2022-09-28 19:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0099_auto_20220928_1908'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='samra_model',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stories', to='sahel.samramodel'),
        ),
    ]

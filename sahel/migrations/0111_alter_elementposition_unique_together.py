# Generated by Django 3.2.15 on 2022-10-13 12:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0110_alter_variable_unit'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='elementposition',
            unique_together={('element', 'story')},
        ),
    ]

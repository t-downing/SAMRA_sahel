# Generated by Django 3.2.14 on 2022-08-31 13:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0062_element_output_variables'),
    ]

    operations = [
        migrations.RenameField(
            model_name='element',
            old_name='output_variables',
            new_name='model_output_variable',
        ),
    ]

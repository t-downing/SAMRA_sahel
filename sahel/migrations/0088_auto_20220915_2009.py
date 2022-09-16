# Generated by Django 3.2.14 on 2022-09-15 20:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0087_auto_20220915_2007'),
    ]

    operations = [
        migrations.RenameField(
            model_name='connection',
            old_name='from_element',
            new_name='from_variable',
        ),
        migrations.RenameField(
            model_name='connection',
            old_name='to_element',
            new_name='to_variable',
        ),
        migrations.AlterUniqueTogether(
            name='connection',
            unique_together={('from_variable', 'to_variable')},
        ),
    ]

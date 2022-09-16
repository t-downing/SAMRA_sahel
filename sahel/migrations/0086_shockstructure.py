# Generated by Django 3.2.14 on 2022-09-15 17:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0085_auto_20220915_1655'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShockStructure',
            fields=[
                ('element_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='sahel.element')),
                ('element_type', models.CharField(choices=[('SE', 'Effet de choc'), ('SH', 'Choc')], default='SE', max_length=2)),
            ],
            options={
                'verbose_name': 'Choc',
            },
            bases=('sahel.element',),
        ),
    ]

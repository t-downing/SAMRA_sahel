# Generated by Django 3.2.15 on 2022-09-28 18:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0094_variableposition'),
    ]

    operations = [
        migrations.CreateModel(
            name='SamraModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
    ]

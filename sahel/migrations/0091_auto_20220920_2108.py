# Generated by Django 3.2.14 on 2022-09-20 21:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sahel', '0090_elementconnection'),
    ]

    operations = [
        migrations.AddField(
            model_name='situationalanalysis',
            name='resilience',
            field=models.CharField(blank=True, choices=[('AA', 'High'), ('BB', 'Medium'), ('CC', 'Low')], max_length=2, null=True),
        ),
        migrations.AddField(
            model_name='situationalanalysis',
            name='status',
            field=models.CharField(blank=True, choices=[('AA', 'Good'), ('BB', 'Medium'), ('CC', 'Bad')], max_length=2, null=True),
        ),
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('elements', models.ManyToManyField(related_name='stories', to='sahel.Element')),
            ],
        ),
    ]

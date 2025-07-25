# Generated by Django 5.1.7 on 2025-04-27 20:10

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UserTracking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(max_length=20)),
                ('facility_type_interest', models.CharField(max_length=255)),
                ('zip_code', models.CharField(max_length=10)),
                ('search_query', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('joined_facility', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]

# Generated by Django 5.1.7 on 2025-03-06 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Facility',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('facility_type', models.CharField(max_length=255)),
                ('endorsement', models.CharField(blank=True, max_length=255, null=True)),
                ('inspection_number', models.CharField(max_length=100, unique=True)),
                ('address', models.TextField()),
                ('state', models.CharField(max_length=50)),
                ('county', models.CharField(max_length=100)),
                ('phone', models.CharField(max_length=20)),
                ('contact', models.CharField(blank=True, max_length=255, null=True)),
                ('contact_person', models.CharField(blank=True, max_length=255, null=True)),
                ('bed_count', models.IntegerField(default=0)),
            ],
        ),
    ]

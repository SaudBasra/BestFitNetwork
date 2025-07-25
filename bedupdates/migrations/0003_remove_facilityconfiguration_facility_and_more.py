# Generated by Django 5.1.7 on 2025-07-11 17:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bedupdates', '0002_bedavailability_last_updated_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='facilityconfiguration',
            name='facility',
        ),
        migrations.AlterUniqueTogether(
            name='room',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='room',
            name='facility',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='last_updated',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='maintenance_beds',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='occupancy_rate',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='occupied_beds',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='private_rooms_available',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='private_rooms_occupied',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='private_rooms_total',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='shared_beds_female_available',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='shared_beds_male_available',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='shared_beds_occupied',
        ),
        migrations.RemoveField(
            model_name='bedavailability',
            name='total_beds',
        ),
        migrations.DeleteModel(
            name='Bed',
        ),
        migrations.DeleteModel(
            name='FacilityConfiguration',
        ),
        migrations.DeleteModel(
            name='Room',
        ),
    ]

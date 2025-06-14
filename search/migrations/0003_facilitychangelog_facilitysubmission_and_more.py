# Generated by Django 5.1.7 on 2025-06-01 13:59

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0002_remove_facility_phone'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FacilityChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('change_type', models.CharField(choices=[('created', 'Created'), ('updated', 'Updated'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('status_change', 'Status Changed'), ('image_update', 'Image Updated')], max_length=20)),
                ('old_values', models.JSONField(blank=True, default=dict)),
                ('new_values', models.JSONField(blank=True, default=dict)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='FacilitySubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submission_notes', models.TextField(blank=True)),
                ('admin_notes', models.TextField(blank=True)),
                ('rejection_reason', models.TextField(blank=True)),
                ('submitter_name', models.CharField(blank=True, max_length=255)),
                ('submitter_email', models.EmailField(blank=True, max_length=254)),
                ('submitter_phone', models.CharField(blank=True, max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AlterModelOptions(
            name='facility',
            options={'ordering': ['-created_at'], 'verbose_name_plural': 'Facilities'},
        ),
        migrations.AddField(
            model_name='facility',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='facility',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_facilities', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='facility',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='facility',
            name='image',
            field=models.ImageField(blank=True, help_text='Facility main image', null=True, upload_to='facilities/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='facility',
            name='meta_description',
            field=models.TextField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name='facility',
            name='search_keywords',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='facility',
            name='slug',
            field=models.SlugField(blank=True, unique=True),
        ),
        migrations.AddField(
            model_name='facility',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('pending', 'Pending Approval'), ('rejected', 'Rejected'), ('draft', 'Draft')], default='pending', max_length=20),
        ),
        migrations.AddField(
            model_name='facility',
            name='submission_type',
            field=models.CharField(choices=[('admin', 'Admin Entry'), ('self_register', 'Self Registration'), ('bulk_import', 'Bulk Import')], default='admin', max_length=20),
        ),
        migrations.AddField(
            model_name='facility',
            name='submitted_by',
            field=models.ForeignKey(blank=True, help_text='Who submitted this facility', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='facility',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name='facility',
            index=models.Index(fields=['status'], name='search_faci_status_619017_idx'),
        ),
        migrations.AddIndex(
            model_name='facility',
            index=models.Index(fields=['facility_type'], name='search_faci_facilit_a47e9b_idx'),
        ),
        migrations.AddIndex(
            model_name='facility',
            index=models.Index(fields=['state', 'county'], name='search_faci_state_90c32a_idx'),
        ),
        migrations.AddField(
            model_name='facilitychangelog',
            name='changed_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='facilitychangelog',
            name='facility',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='search.facility'),
        ),
        migrations.AddField(
            model_name='facilitysubmission',
            name='facility',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='search.facility'),
        ),
    ]

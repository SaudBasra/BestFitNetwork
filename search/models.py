# search/models.py - Enhanced Facility Model
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse

class Facility(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
        ('draft', 'Draft')
    ]
    
    SUBMISSION_TYPE_CHOICES = [
        ('admin', 'Admin Entry'),
        ('self_register', 'Self Registration'),
        ('bulk_import', 'Bulk Import')
    ]

    # Basic Information (existing)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    facility_type = models.CharField(max_length=255)
    endorsement = models.CharField(max_length=255, blank=True, null=True)
    inspection_number = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    state = models.CharField(max_length=50)
    county = models.CharField(max_length=100)
    contact = models.CharField(max_length=255, blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    bed_count = models.IntegerField(default=0)
    
    # New Administrative Fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Image Field
    image = models.ImageField(
        upload_to='facilities/%Y/%m/', 
        blank=True, 
        null=True,
        help_text="Facility main image"
    )
    
    # Submission tracking
    submitted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Who submitted this facility"
    )
    submission_type = models.CharField(
        max_length=20, 
        choices=SUBMISSION_TYPE_CHOICES, 
        default='admin'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_facilities'
    )
    
    # SEO & Search
    meta_description = models.TextField(blank=True, max_length=160)
    search_keywords = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Facilities"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['facility_type']),
            models.Index(fields=['state', 'county']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('facility_detail', kwargs={'facility_id': self.id})

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return '/static/images/default-facility.jpg'

    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_active(self):
        return self.status == 'active'


class FacilitySubmission(models.Model):
    """Track submission details and approval process"""
    facility = models.OneToOneField(Facility, on_delete=models.CASCADE)
    submission_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Contact information for self-registrations
    submitter_name = models.CharField(max_length=255, blank=True)
    submitter_email = models.EmailField(blank=True)
    submitter_phone = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Submission for {self.facility.name}"


class FacilityChangeLog(models.Model):
    """Audit trail for all facility changes"""
    CHANGE_TYPE_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('status_change', 'Status Changed'),
        ('image_update', 'Image Updated')
    ]
    
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.change_type} - {self.facility.name} by {self.changed_by}"
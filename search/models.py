# search/models.py - Complete file with FacilityPricing
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from decimal import Decimal
from django.core.exceptions import ValidationError
import re

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

    # Basic Information (updated)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    facility_type = models.CharField(max_length=255)
    endorsement = models.CharField(max_length=255, blank=True, null=True)
    credential_number = models.CharField(
        max_length=100, 
        unique=True, 
        help_text="Can be full format (12345-AGC-2) or just the number (12345)"
    )
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
            models.Index(fields=['credential_number']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        """Validate credential number format"""
        if self.credential_number:
            if not self.is_valid_credential_format(self.credential_number):
                raise ValidationError({
                    'credential_number': 'Invalid format. Expected: 2-5 digits or XXXXX-AGC-X format'
                })

    def get_absolute_url(self):
        return reverse('search:facility_detail', kwargs={'facility_id': self.id})

    def get_registration_number(self):
        """Extract the essential number part (before -AGC if present)"""
        if '-AGC' in self.credential_number:
            return self.credential_number.split('-AGC')[0]
        return self.credential_number

    def get_display_credential(self):
        """Get credential for display - show full format if available, otherwise just the number"""
        if '-AGC' in self.credential_number:
            return self.credential_number  # Full format like 23242-AGC-2
        else:
            return self.credential_number  # Just the number like 23242

    def has_full_credential_format(self):
        """Check if credential has the full AGC format"""
        return '-AGC' in self.credential_number

    @staticmethod
    def is_valid_credential_format(credential):
        """Validate credential number format - accepts both formats"""
        if not credential:
            return False
        
        # Check if it's just a number (2-5 digits)
        if re.match(r'^\d{2,5}$', credential):
            return True
        
        # Check if it's full format (2-5 digits + AGC + suffix)
        if re.match(r'^\d{2,5}-AGC-\d+$', credential):
            return True
            
        return False

    @staticmethod
    def extract_registration_number(credential):
        """Extract registration number from credential (the essential part)"""
        if not credential:
            return credential
        if '-AGC' in credential:
            return credential.split('-AGC')[0]
        return credential

    @staticmethod
    def find_by_registration_number(registration_number):
        """Find facility by registration number (the essential part)"""
        if not registration_number:
            return None
        
        # Try exact match first (for cases where credential is just the number)
        facility = Facility.objects.filter(credential_number=registration_number).first()
        if facility:
            return facility
        
        # Try prefix match (for cases where credential has AGC format)
        facility = Facility.objects.filter(
            credential_number__startswith=f"{registration_number}-AGC"
        ).first()
        return facility

    @staticmethod
    def normalize_credential_input(input_credential):
        """Normalize credential input for storage"""
        if not input_credential:
            return input_credential
        
        # If it's already in a valid format, keep it
        if Facility.is_valid_credential_format(input_credential):
            return input_credential
        
        # If it's just digits, validate length
        clean_input = re.sub(r'[^\d]', '', input_credential)
        if len(clean_input) >= 2 and len(clean_input) <= 5:
            return clean_input
        
        return input_credential  # Return as-is if can't normalize

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
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.change_type} - {self.facility.name} by {self.changed_by}"
    
    def get_absolute_url(self):
        return reverse('search:facility_detail', kwargs={'facility_id': self.id})


class FacilityPricing(models.Model):
    """Simple pricing model for facility private and shared beds"""
    
    facility = models.OneToOneField(
        Facility,
        on_delete=models.CASCADE,
        related_name='pricing'
    )
    
    # Private bed pricing (monthly rates)
    private_bed_min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum monthly rate for private beds"
    )
    
    private_bed_max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum monthly rate for private beds"
    )
    
    # Shared bed pricing (monthly rates)
    shared_bed_min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum monthly rate for shared beds"
    )
    
    shared_bed_max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum monthly rate for shared beds"
    )
    
    # Additional information
    notes = models.TextField(
        blank=True,
        help_text="Additional pricing notes or conditions"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_facility_pricing'
    )
    
    class Meta:
        verbose_name = 'Facility Pricing'
        verbose_name_plural = 'Facility Pricing'
    
    def __str__(self):
        return f"Pricing for {self.facility.name}"
    
    @property
    def private_bed_display(self):
        """Display format for private bed pricing"""
        if not self.private_bed_min_price and not self.private_bed_max_price:
            return "Not Available"
        
        min_price = self.private_bed_min_price or 0
        max_price = self.private_bed_max_price or 0
        
        if min_price == max_price and min_price > 0:
            return f"${min_price:,.0f}/month"
        elif min_price > 0 and max_price > 0:
            return f"${min_price:,.0f} - ${max_price:,.0f}/month"
        elif min_price > 0:
            return f"From ${min_price:,.0f}/month"
        elif max_price > 0:
            return f"Up to ${max_price:,.0f}/month"
        else:
            return "Not Available"
    
    @property
    def shared_bed_display(self):
        """Display format for shared bed pricing"""
        if not self.shared_bed_min_price and not self.shared_bed_max_price:
            return "Not Available"
        
        min_price = self.shared_bed_min_price or 0
        max_price = self.shared_bed_max_price or 0
        
        if min_price == max_price and min_price > 0:
            return f"${min_price:,.0f}/month"
        elif min_price > 0 and max_price > 0:
            return f"${min_price:,.0f} - ${max_price:,.0f}/month"
        elif min_price > 0:
            return f"From ${min_price:,.0f}/month"
        elif max_price > 0:
            return f"Up to ${max_price:,.0f}/month"
        else:
            return "Not Available"
    
    @property
    def has_pricing_info(self):
        """Check if any pricing information is available"""
        return any([
            self.private_bed_min_price,
            self.private_bed_max_price,
            self.shared_bed_min_price,
            self.shared_bed_max_price
        ])
    
    def clean(self):
        """Validate pricing data"""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # Validate private bed pricing
        if self.private_bed_min_price and self.private_bed_max_price:
            if self.private_bed_min_price > self.private_bed_max_price:
                errors['private_bed_max_price'] = "Maximum price cannot be less than minimum price"
        
        # Validate shared bed pricing
        if self.shared_bed_min_price and self.shared_bed_max_price:
            if self.shared_bed_min_price > self.shared_bed_max_price:
                errors['shared_bed_max_price'] = "Maximum price cannot be less than minimum price"
        
        if errors:
            raise ValidationError(errors)
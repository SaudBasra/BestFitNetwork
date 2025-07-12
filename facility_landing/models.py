# facility_landing/models.py

from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from search.models import Facility
import uuid
import os


def gallery_upload_path(instance, filename):
    """Generate upload path for gallery images"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f'facility_landing/{instance.facility.id}/gallery/{filename}'


def hero_upload_path(instance, filename):
    """Generate upload path for hero images"""
    ext = filename.split('.')[-1]
    filename = f"hero_{uuid.uuid4()}.{ext}"
    return f'facility_landing/{instance.facility.id}/hero/{filename}'


class FacilityLandingPage(models.Model):
    """Main landing page model for each facility"""
    
    facility = models.OneToOneField(
        Facility, 
        on_delete=models.CASCADE,
        related_name='landing_page'
    )
    
    # Hero Section
    hero_image = models.ImageField(
        upload_to=hero_upload_path,
        blank=True,
        null=True,
        help_text="Main hero image for the landing page (recommended: 1920x1080px)"
    )
    hero_tagline = models.CharField(
        max_length=200,
        blank=True,
        help_text="Compelling tagline shown in hero section"
    )
    hero_description = models.TextField(
        max_length=500,
        blank=True,
        help_text="Brief description shown in hero section"
    )
    
    # About Us Section
    mission_statement = models.TextField(
        blank=True,
        help_text="Facility's mission and philosophy of care"
    )
    facility_story = models.TextField(
        blank=True,
        help_text="History and background of the facility"
    )
    years_of_experience = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of years in operation"
    )
    
    # Services & Care
    services_description = models.TextField(
        blank=True,
        help_text="Detailed description of services and care provided"
    )
    specialized_care = models.TextField(
        blank=True,
        help_text="Specialized care programs and treatments"
    )
    
    # Accreditations & Certifications
    accreditations = models.TextField(
        blank=True,
        help_text="List of accreditations, certifications, and awards"
    )
    
    # Additional Information
    amenities = models.TextField(
        blank=True,
        help_text="Facility amenities and features (comma-separated or paragraph format)"
    )
    staff_credentials = models.TextField(
        blank=True,
        help_text="Information about staff qualifications and training"
    )
    
    # Contact & Availability
    visiting_hours = models.CharField(
        max_length=200,
        blank=True,
        help_text="Visiting hours information"
    )
    tour_available = models.BooleanField(
        default=True,
        help_text="Whether facility tours are available"
    )
    
    # SEO & Meta
    meta_title = models.CharField(
        max_length=60,
        blank=True,
        help_text="Custom page title for SEO (max 60 characters)"
    )
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        help_text="Custom meta description for SEO (max 160 characters)"
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_landing_pages'
    )
    
    # Status
    is_published = models.BooleanField(
        default=True,
        help_text="Whether the landing page is publicly visible"
    )
    
    class Meta:
        verbose_name = "Facility Landing Page"
        verbose_name_plural = "Facility Landing Pages"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.facility.name} - Landing Page"
    
    def get_absolute_url(self):
        """Return the public URL for this landing page"""
        return reverse('facility_landing:public_page', kwargs={'facility_id': self.facility.id})
    
    def get_edit_url(self):
        """Return the edit URL for facility staff"""
        return reverse('facility_landing:edit_page', kwargs={'facility_id': self.facility.id})
    
    @property
    def hero_title(self):
        """Return hero title, fallback to facility name"""
        return self.hero_tagline or self.facility.name
    
    @property
    def page_title(self):
        """Return page title for SEO"""
        if self.meta_title:
            return self.meta_title
        return f"{self.facility.name} - Healthcare Facility"
    
    @property
    def page_description(self):
        """Return page description for SEO"""
        if self.meta_description:
            return self.meta_description
        if self.hero_description:
            return self.hero_description[:160]
        return f"Learn more about {self.facility.name}, a {self.facility.facility_type} located in {self.facility.address}."


class FacilityGallery(models.Model):
    """Gallery images for facility landing pages"""
    
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name='gallery_images'
    )
    
    image = models.ImageField(
        upload_to=gallery_upload_path,
        help_text="Gallery image (recommended: 800x600px or higher)"
    )
    
    title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Image title/caption"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the image"
    )
    
    category = models.CharField(
        max_length=50,
        choices=[
            ('rooms', 'Rooms & Living Spaces'),
            ('common', 'Common Areas'),
            ('dining', 'Dining Areas'),
            ('activities', 'Activities & Recreation'),
            ('exterior', 'Exterior & Grounds'),
            ('staff', 'Staff & Care'),
            ('amenities', 'Amenities'),
            ('other', 'Other'),
        ],
        default='other',
        help_text="Category for organizing gallery images"
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order to display images (lower numbers first)"
    )
    
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether this image is featured prominently"
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = "Gallery Image"
        verbose_name_plural = "Gallery Images"
        ordering = ['display_order', '-uploaded_at']
    
    def __str__(self):
        return f"{self.facility.name} - {self.title or 'Gallery Image'}"


class FacilityTestimonial(models.Model):
    """Testimonials and reviews for facility landing pages"""
    
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name='testimonials'
    )
    
    author_name = models.CharField(
        max_length=100,
        help_text="Name of the person giving testimonial"
    )
    
    author_relation = models.CharField(
        max_length=50,
        choices=[
            ('resident', 'Resident'),
            ('family', 'Family Member'),
            ('visitor', 'Visitor'),
            ('professional', 'Healthcare Professional'),
            ('other', 'Other'),
        ],
        default='family',
        help_text="Relationship to the facility"
    )
    
    testimonial_text = models.TextField(
        help_text="The testimonial content"
    )
    
    rating = models.PositiveIntegerField(
        choices=[(i, f"{i} Star{'s' if i != 1 else ''}") for i in range(1, 6)],
        null=True,
        blank=True,
        help_text="Star rating (1-5)"
    )
    
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether to feature this testimonial prominently"
    )
    
    is_approved = models.BooleanField(
        default=False,
        help_text="Whether this testimonial has been approved for display"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_testimonials'
    )
    
    class Meta:
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"
        ordering = ['-is_featured', '-created_at']
    
    def __str__(self):
        return f"Testimonial by {self.author_name} for {self.facility.name}"


class LandingPageView(models.Model):
    """Track landing page views for analytics"""
    
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name='page_views'
    )
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True, null=True)
    
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Page View"
        verbose_name_plural = "Page Views"
        ordering = ['-viewed_at']
    
    def __str__(self):
        return f"View of {self.facility.name} at {self.viewed_at}"


# Signal to create default landing page when facility is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Facility)
def create_default_landing_page(sender, instance, created, **kwargs):
    """Create a default landing page when a new facility is created"""
    if created:
        FacilityLandingPage.objects.get_or_create(
            facility=instance,
            defaults={
                'hero_tagline': f"Welcome to {instance.name}",
                'hero_description': f"Quality care and comfortable living at {instance.name}.",
                'mission_statement': "Our mission is to provide exceptional care and support to our residents in a warm, welcoming environment.",
                'services_description': f"At {instance.name}, we offer comprehensive care services tailored to meet the unique needs of each resident.",
                'is_published': True,
            }
        )
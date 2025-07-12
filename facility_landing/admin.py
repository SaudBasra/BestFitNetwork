# facility_landing/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import FacilityLandingPage, FacilityGallery, FacilityTestimonial, LandingPageView


@admin.register(FacilityLandingPage)
class FacilityLandingPageAdmin(admin.ModelAdmin):
    list_display = ['facility_name', 'is_published', 'updated_at', 'view_public_page', 'last_updated_by']
    list_filter = ['is_published', 'updated_at', 'created_at']
    search_fields = ['facility__name', 'hero_tagline', 'meta_title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Facility', {
            'fields': ('facility',)
        }),
        ('Hero Section', {
            'fields': ('hero_image', 'hero_tagline', 'hero_description', 'years_of_experience')
        }),
        ('About Us', {
            'fields': ('mission_statement', 'facility_story')
        }),
        ('Services & Care', {
            'fields': ('services_description', 'specialized_care', 'accreditations')
        }),
        ('Additional Details', {
            'fields': ('amenities', 'staff_credentials', 'visiting_hours', 'tour_available')
        }),
        ('SEO Settings', {
            'fields': ('meta_title', 'meta_description')
        }),
        ('Publishing', {
            'fields': ('is_published',)
        }),
        ('Tracking', {
            'fields': ('created_at', 'updated_at', 'last_updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def facility_name(self, obj):
        return obj.facility.name
    facility_name.short_description = 'Facility'
    facility_name.admin_order_field = 'facility__name'
    
    def view_public_page(self, obj):
        if obj.pk:
            url = reverse('facility_landing:public_page', args=[obj.facility.id])
            return format_html('<a href="{}" target="_blank">View Page</a>', url)
        return "-"
    view_public_page.short_description = 'Public Page'


@admin.register(FacilityGallery)
class FacilityGalleryAdmin(admin.ModelAdmin):
    list_display = ['facility_name', 'title', 'category', 'is_featured', 'uploaded_at', 'image_preview']
    list_filter = ['category', 'is_featured', 'uploaded_at']
    search_fields = ['facility__name', 'title', 'description']
    readonly_fields = ['uploaded_at']
    
    fieldsets = (
        ('Image Details', {
            'fields': ('facility', 'image', 'title', 'description')
        }),
        ('Organization', {
            'fields': ('category', 'display_order', 'is_featured')
        }),
        ('Tracking', {
            'fields': ('uploaded_at', 'uploaded_by'),
            'classes': ('collapse',)
        }),
    )
    
    def facility_name(self, obj):
        return obj.facility.name
    facility_name.short_description = 'Facility'
    facility_name.admin_order_field = 'facility__name'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "-"
    image_preview.short_description = 'Preview'


@admin.register(FacilityTestimonial)
class FacilityTestimonialAdmin(admin.ModelAdmin):
    list_display = ['facility_name', 'author_name', 'author_relation', 'rating', 'is_featured', 'is_approved', 'created_at']
    list_filter = ['author_relation', 'rating', 'is_featured', 'is_approved', 'created_at']
    search_fields = ['facility__name', 'author_name', 'testimonial_text']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Testimonial Details', {
            'fields': ('facility', 'author_name', 'author_relation', 'testimonial_text', 'rating')
        }),
        ('Status', {
            'fields': ('is_featured', 'is_approved', 'approved_by')
        }),
        ('Tracking', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def facility_name(self, obj):
        return obj.facility.name
    facility_name.short_description = 'Facility'
    facility_name.admin_order_field = 'facility__name'


@admin.register(LandingPageView)
class LandingPageViewAdmin(admin.ModelAdmin):
    list_display = ['facility_name', 'ip_address', 'viewed_at', 'referer_domain']
    list_filter = ['viewed_at']
    search_fields = ['facility__name', 'ip_address']
    readonly_fields = ['facility', 'ip_address', 'user_agent', 'referer', 'viewed_at']
    
    def facility_name(self, obj):
        return obj.facility.name
    facility_name.short_description = 'Facility'
    facility_name.admin_order_field = 'facility__name'
    
    def referer_domain(self, obj):
        if obj.referer:
            from urllib.parse import urlparse
            domain = urlparse(obj.referer).netloc
            return domain or obj.referer[:50]
        return "-"
    referer_domain.short_description = 'Referer Domain'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
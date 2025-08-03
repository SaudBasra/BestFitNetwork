# bedupdates/admin.py - Admin interface for bed management

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import FacilityConfiguration, Room, Bed, BedAvailability

@admin.register(FacilityConfiguration)
class FacilityConfigurationAdmin(admin.ModelAdmin):
    list_display = ('facility', 'is_configured', 'total_rooms', 'get_total_beds', 'created_at', 'updated_at')
    list_filter = ('is_configured', 'created_at', 'updated_at')
    search_fields = ('facility__name', 'facility__credential_number')
    readonly_fields = ('created_at', 'updated_at', 'get_total_beds', 'get_bed_breakdown')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('facility', 'is_configured', 'total_rooms')
        }),
        ('Statistics', {
            'fields': ('get_total_beds', 'get_bed_breakdown'),
            'classes': ('collapse',)
        }),
        ('Configuration Data', {
            'fields': ('configuration_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_total_beds(self, obj):
        return obj.get_total_beds()
    get_total_beds.short_description = 'Total Beds'
    
    def get_bed_breakdown(self, obj):
        breakdown = obj.get_bed_counts_by_type()
        return format_html(
            '<strong>Private:</strong> {} | <strong>Shared:</strong> {} | <strong>Total:</strong> {}',
            breakdown['private_beds'],
            breakdown['shared_beds'],
            breakdown['total_beds']
        )
    get_bed_breakdown.short_description = 'Bed Breakdown'

class BedInline(admin.TabularInline):
    model = Bed
    extra = 0
    fields = ('bed_number', 'bed_id', 'status', 'gender', 'patient_name', 'admitted_date')
    readonly_fields = ('bed_id', 'created_at', 'updated_at')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_name', 'facility_name', 'room_type', 'room_gender', 'get_total_beds', 'get_occupied_beds', 'is_active')
    list_filter = ('room_type', 'room_gender', 'is_active', 'created_at')
    search_fields = ('room_name', 'facility_config__facility__name', 'room_number')
    inlines = [BedInline]
    
    fieldsets = (
        ('Room Information', {
            'fields': ('facility_config', 'room_name', 'room_number', 'room_type', 'room_gender', 'is_active')
        }),
        ('Statistics', {
            'fields': ('get_total_beds', 'get_occupied_beds', 'get_vacant_beds'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'get_total_beds', 'get_occupied_beds', 'get_vacant_beds')
    
    def facility_name(self, obj):
        return obj.facility_config.facility.name
    facility_name.short_description = 'Facility'
    facility_name.admin_order_field = 'facility_config__facility__name'
    
    def get_total_beds(self, obj):
        return obj.get_total_beds()
    get_total_beds.short_description = 'Total Beds'
    
    def get_occupied_beds(self, obj):
        return obj.get_occupied_beds()
    get_occupied_beds.short_description = 'Occupied Beds'
    
    def get_vacant_beds(self, obj):
        return obj.get_vacant_beds()
    get_vacant_beds.short_description = 'Vacant Beds'

@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('bed_id', 'room_name', 'facility_name', 'bed_number', 'status', 'gender', 'patient_name', 'admitted_date')
    list_filter = ('status', 'gender', 'room__room_type', 'admitted_date', 'created_at')
    search_fields = ('bed_id', 'bed_number', 'patient_name', 'room__room_name', 'room__facility_config__facility__name')
    
    fieldsets = (
        ('Bed Information', {
            'fields': ('room', 'bed_number', 'bed_id')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'gender', 'patient_name', 'admitted_date')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('bed_id', 'created_at', 'updated_at')
    
    def room_name(self, obj):
        return obj.room.room_name
    room_name.short_description = 'Room'
    room_name.admin_order_field = 'room__room_name'
    
    def facility_name(self, obj):
        return obj.room.facility_config.facility.name
    facility_name.short_description = 'Facility'
    facility_name.admin_order_field = 'room__facility_config__facility__name'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Trigger room gender update for shared rooms
        if obj.room.room_type == 'shared':
            obj.room.update_room_gender_from_occupancy()

# Legacy model admin (for backward compatibility)
@admin.register(BedAvailability)
class BedAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('facility', 'available_beds', 'shared_beds_total', 'separate_beds_total', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('facility__name', 'facility__credential_number')
    readonly_fields = ('updated_at',)
    
    fieldsets = (
        ('Facility', {
            'fields': ('facility',)
        }),
        ('Bed Availability', {
            'fields': ('available_beds',)
        }),
        ('Shared Beds', {
            'fields': ('shared_beds_total', 'shared_beds_male', 'shared_beds_female')
        }),
        ('Private Beds', {
            'fields': ('separate_beds_total', 'separate_beds_male', 'separate_beds_female')
        }),
        ('Timestamps', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # editing existing object
            readonly.append('facility')
        return readonly

# Custom admin site title and header
admin.site.site_title = "Bed Management Admin"
admin.site.site_header = "Bed Management Administration"
admin.site.index_title = "Bed Management System"
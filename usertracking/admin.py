# usertracking/admin.py
from django.contrib import admin
from .models import UserTracking

@admin.register(UserTracking)
class UserTrackingAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'facility_type_interest', 'zip_code', 
                    'search_query', 'timestamp', 'joined_facility')
    list_filter = ('facility_type_interest', 'joined_facility', 'timestamp')
    search_fields = ('name', 'email', 'phone', 'search_query', 'zip_code')
    date_hierarchy = 'timestamp'
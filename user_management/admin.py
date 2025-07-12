# user_management/admin.py - Updated with Facility User Creation

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserProfile, UserSession, LoginAttempt
from search.models import Facility

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('user_type', 'facility', 'position', 'phone_number', 'job_title', 'bio', 'is_verified')

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    
    def user_type(self, obj):
        """Display user type from profile"""
        if hasattr(obj, 'user_profile'):
            return obj.user_profile.get_user_type_display()
        return 'No Profile'
    user_type.short_description = 'User Type'
    
    def facility(self, obj):
        """Display facility from profile"""
        if hasattr(obj, 'user_profile') and obj.user_profile.facility:
            return obj.user_profile.facility.name
        return 'No Facility'
    facility.short_description = 'Facility'
    
    def facility_status(self, obj):
        """Display facility status"""
        if hasattr(obj, 'user_profile') and obj.user_profile.facility:
            facility = obj.user_profile.facility
            if facility.status == 'active':
                return format_html('<span style="color: green;">●</span> Active')
            else:
                return format_html('<span style="color: red;">●</span> {}', facility.get_status_display())
        return '-'
    facility_status.short_description = 'Facility Status'
    
    # Add custom methods to list display
    list_display = BaseUserAdmin.list_display + ('user_type', 'facility', 'facility_status')
    list_filter = BaseUserAdmin.list_filter + ('user_profile__user_type', 'user_profile__facility__status')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user_profile__facility')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'facility', 'position', 'is_verified', 'created_at']
    list_filter = ['user_type', 'facility', 'is_verified', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'facility')

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'device_type', 'browser', 'login_time', 'is_active']
    list_filter = ['device_type', 'browser', 'is_active', 'login_time']
    search_fields = ['user__username', 'ip_address']
    readonly_fields = ['session_key', 'login_time', 'last_activity']

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'attempt_type', 'ip_address', 'timestamp', 'failure_reason']
    list_filter = ['attempt_type', 'timestamp']
    search_fields = ['username', 'ip_address', 'inspection_number']
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-timestamp')

# Custom admin action to create facility users
def create_facility_users_for_active_facilities(modeladmin, request, queryset):
    """Create facility staff users for selected active facilities"""
    created_count = 0
    errors = []
    
    for facility in queryset.filter(status='active'):
        try:
            # Check if user already exists
            if User.objects.filter(username=facility.inspection_number).exists():
                continue
            
            # Create user
            if facility.contact_person:
                name_parts = facility.contact_person.split()
                first_name = name_parts[0] if name_parts else 'Facility'
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Staff'
            else:
                first_name = 'Facility'
                last_name = 'Staff'
            
            user = User.objects.create_user(
                username=facility.inspection_number,
                password='bestfit#123',
                first_name=first_name,
                last_name=last_name,
                email=f"{facility.inspection_number}@facility.bestfit.com",
                is_active=True
            )
            
            # Create profile
            UserProfile.objects.create(
                user=user,
                user_type='facility_staff',
                facility=facility,
                position='Facility Staff',
                phone_number=facility.contact if facility.contact else None,
                is_verified=True
            )
            
            created_count += 1
            
        except Exception as e:
            errors.append(f"{facility.name}: {str(e)}")
    
    if created_count > 0:
        messages.success(request, f"Successfully created {created_count} facility staff accounts.")
    
    if errors:
        messages.error(request, f"Errors occurred: {'; '.join(errors)}")

create_facility_users_for_active_facilities.short_description = "Create facility staff users for selected active facilities"

# Add the action to Facility admin if it exists
try:
    from search.admin import FacilityAdmin
    if hasattr(FacilityAdmin, 'actions'):
        FacilityAdmin.actions = list(FacilityAdmin.actions) + [create_facility_users_for_active_facilities]
    else:
        FacilityAdmin.actions = [create_facility_users_for_active_facilities]
except ImportError:
    pass

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
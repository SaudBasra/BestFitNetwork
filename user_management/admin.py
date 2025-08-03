# user_management/admin.py - Updated for credential number system

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
    search_fields = ['username', 'ip_address', 'registration_number', 'credential_number']  # Updated field names
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-timestamp')

# Custom admin action to create facility users
def create_facility_users_for_active_facilities(modeladmin, request, queryset):
    """Create facility users for selected active facilities"""
    created_count = 0
    error_count = 0
    
    for facility in queryset.filter(status='active'):
        try:
            username = facility.credential_number  # Updated to use credential_number
            
            if User.objects.filter(username=username).exists():
                continue
            
            # Create user
            user = User.objects.create_user(
                username=username,
                password='bestfit#123',
                first_name=facility.contact_person.split()[0] if facility.contact_person else 'Facility',
                last_name=' '.join(facility.contact_person.split()[1:]) if facility.contact_person and len(facility.contact_person.split()) > 1 else 'Staff',
                email=f"{facility.credential_number}@facility.bestfit.local"
            )
            
            # Create profile
            UserProfile.objects.create(
                user=user,
                user_type='facility_staff',
                facility=facility,
                phone_number=facility.contact or '',
                position='Facility Staff'
            )
            
            created_count += 1
            
        except Exception as e:
            error_count += 1
            messages.error(request, f'Error creating user for {facility.name}: {str(e)}')
    
    if created_count > 0:
        messages.success(request, f'Successfully created {created_count} facility user accounts.')
    if error_count > 0:
        messages.error(request, f'{error_count} facilities had errors during user creation.')

create_facility_users_for_active_facilities.short_description = "Create facility users for selected facilities"

# Re-register User admin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
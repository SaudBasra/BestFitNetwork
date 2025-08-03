# user_management/models.py - Updated for credential number system

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class UserProfile(models.Model):
    """Profile extension for Django's default User model"""
    
    USER_TYPES = [
        ('super_admin', 'Super Administrator'),
        ('search_admin', 'Search Engine Administrator'), 
        ('facility_staff', 'Facility Staff'),
        ('facility_admin', 'Facility Administrator'),
        ('public_user', 'Public User'),
        ('api_user', 'API User'),
        ('support_staff', 'Support Staff'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='user_profile'
    )
    
    # User type and relationships
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPES, 
        default='public_user'
    )
    
    facility = models.ForeignKey(
        'search.Facility', 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True, 
        related_name='staff_users'
    )
    
    position = models.CharField(max_length=100, blank=True, null=True)
    
    # Profile information
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='user_profiles/%Y/%m/', 
        blank=True, 
        null=True
    )
    
    # Additional fields
    is_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    
    # Professional information
    organization = models.CharField(max_length=200, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    newsletter_subscription = models.BooleanField(default=False)
    
    # Privacy settings
    profile_visibility = models.CharField(
        max_length=20,
        choices=[
            ('public', 'Public'),
            ('private', 'Private'),
            ('facility_only', 'Facility Only'),
        ],
        default='private'
    )
    
    # Facility-specific data
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    hire_date = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"
    
    def get_full_name(self):
        """Return full name or username"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        elif self.user.first_name:
            return self.user.first_name
        return self.user.username
    
    def is_facility_user(self):
        """Check if user is facility-related"""
        return self.user_type in ['facility_staff', 'facility_admin']
    
    def is_admin_user(self):
        """Check if user has admin privileges"""
        return self.user_type in ['super_admin', 'search_admin'] or self.user.is_superuser
    
    def can_access_facility(self, facility):
        """Check if user can access specific facility"""
        if self.is_admin_user():
            return True
        return self.facility == facility if self.facility else False


class UserSession(models.Model):
    """Track user sessions for security and analytics"""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='user_sessions'
    )
    
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_type = models.CharField(max_length=50, blank=True, null=True)
    browser = models.CharField(max_length=50, blank=True, null=True)
    
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_time = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
    
    def duration(self):
        """Calculate session duration"""
        end_time = self.logout_time or timezone.now()
        return end_time - self.login_time


class LoginAttempt(models.Model):
    """Track login attempts for security"""
    
    ATTEMPT_TYPES = [
        ('success', 'Successful Login'),
        ('failure', 'Failed Login'),
        ('blocked', 'Blocked Attempt'),
    ]
    
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    attempt_type = models.CharField(max_length=20, choices=ATTEMPT_TYPES)
    failure_reason = models.CharField(max_length=200, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional context for facility staff login attempts - UPDATED FOR CREDENTIAL SYSTEM
    registration_number = models.CharField(max_length=100, blank=True, null=True, 
                                         help_text="Registration number used for facility login")
    credential_number = models.CharField(max_length=100, blank=True, null=True,
                                       help_text="Full credential number of facility")
    contact_person_attempted = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.username} - {self.attempt_type} - {self.timestamp}"
# user_management/backends.py - Updated to not interfere with form validation

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from search.models import Facility
from .models import UserProfile, LoginAttempt
import logging

logger = logging.getLogger(__name__)

class FacilityAuthenticationBackend(BaseBackend):
    """
    Updated backend - only handles ACTIVE facilities
    Status checking is now done in the form for better error messages
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate facility staff - only for ACTIVE facilities
        (Status checking is now handled in the form)
        """
        
        print("\n" + "="*80)
        print("🏥 BACKEND AUTHENTICATION ATTEMPT")
        print("="*80)
        print(f"📋 Username (Inspection #): '{username}'")
        print(f"🔑 Password provided: {'✅ Yes' if password else '❌ No'}")
        
        # Step 1: Basic validation
        if not username or not password:
            print("❌ BACKEND: Missing username or password")
            print("="*80)
            return None
        
        # Step 2: Skip if this looks like admin login
        if '@' in username or len(username) < 3:
            print("🔄 BACKEND: Looks like admin login, skipping")
            print("="*80)
            return None
        
        # Step 3: Check password
        if password != 'bestfit#123':
            print(f"❌ BACKEND: Incorrect password")
            self._log_failed_attempt(request, username, 'incorrect_password')
            print("="*80)
            return None
        
        print("✅ BACKEND: Password correct")
        
        # Step 4: Find facility
        try:
            facility = Facility.objects.get(inspection_number=username)
            print(f"✅ BACKEND: Found facility {facility.name}")
            
            # Step 5: Check if facility is active (backend only handles active)
            if facility.status != 'active':
                print(f"❌ BACKEND: Facility not active ({facility.status}) - letting form handle this")
                self._log_failed_attempt(request, username, f'facility_status_{facility.status}')
                print("="*80)
                return None
            
            print("✅ BACKEND: Facility is active")
            
        except Facility.DoesNotExist:
            print(f"❌ BACKEND: Facility not found")
            self._log_failed_attempt(request, username, 'facility_not_found')
            print("="*80)
            return None
        
        # Step 6: Create/get user
        try:
            user = self._get_or_create_facility_user(facility)
            if user:
                print(f"✅ BACKEND SUCCESS: {user.username}")
                self._log_successful_attempt(request, username)
                print("="*80)
                return user
            else:
                print("❌ BACKEND: Failed to create user")
                print("="*80)
                return None
                
        except Exception as e:
            print(f"❌ BACKEND ERROR: {str(e)}")
            self._log_failed_attempt(request, username, f'user_error_{str(e)}')
            print("="*80)
            return None
    
    def get_user(self, user_id):
        """Get user by ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    
    def _get_or_create_facility_user(self, facility):
        """Get or create user account with proper profile setup"""
        
        username = facility.inspection_number
        print(f"   🔍 BACKEND: Looking for user {username}")
        
        try:
            # Try to get existing user
            user = User.objects.get(username=username)
            print(f"   ✅ BACKEND: Found existing user")
            
            if not user.is_active:
                user.is_active = True
                user.save()
                print("   🔄 BACKEND: Activated user")
            
        except User.DoesNotExist:
            # Create new user
            print(f"   🆕 BACKEND: Creating new user")
            
            if facility.contact_person:
                name_parts = facility.contact_person.split()
                first_name = name_parts[0] if name_parts else 'Facility'
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Staff'
            else:
                first_name = 'Facility'
                last_name = 'Staff'
            
            user = User.objects.create_user(
                username=username,
                password='bestfit#123',
                first_name=first_name,
                last_name=last_name,
                email=f"{username}@facility.bestfit.com",
                is_active=True
            )
            print(f"   ✅ BACKEND: Created user {username}")
        
        # Ensure profile is set up correctly
        try:
            profile = UserProfile.objects.get(user=user)
            print(f"   ✅ BACKEND: Found profile")
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)
            print(f"   🆕 BACKEND: Created profile")
        
        # Always update profile settings
        profile.user_type = 'facility_staff'
        profile.facility = facility
        profile.position = 'Facility Staff'
        profile.is_verified = True
        profile.save()
        print(f"   ✅ BACKEND: Updated profile")
        
        return user
    
    def _log_successful_attempt(self, request, username):
        """Log successful login attempt"""
        try:
            LoginAttempt.objects.create(
                username=username,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                attempt_type='success',
                inspection_number=username
            )
        except Exception as e:
            print(f"   ⚠️  Could not log success: {str(e)}")
    
    def _log_failed_attempt(self, request, username, reason):
        """Log failed login attempt"""
        try:
            LoginAttempt.objects.create(
                username=username,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                attempt_type='failure',
                failure_reason=reason,
                inspection_number=username
            )
        except Exception as e:
            print(f"   ⚠️  Could not log failure: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        if not request:
            return '127.0.0.1'
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR', '127.0.0.1')
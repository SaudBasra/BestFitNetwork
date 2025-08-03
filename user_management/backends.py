# user_management/backends.py - Updated for credential number system

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from search.models import Facility
from .models import UserProfile, LoginAttempt
import logging

logger = logging.getLogger(__name__)

class FacilityAuthenticationBackend(BaseBackend):
    """
    Updated backend for credential number system
    Handles both simple number format and full AGC format
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate facility staff using credential number system
        Username should be the full credential number (e.g., "23242-AGC-2" or "23242")
        """
        
        print("\n" + "="*80)
        print("🏥 BACKEND AUTHENTICATION ATTEMPT")
        print("="*80)
        print(f"📋 Username (Credential): '{username}'")
        print(f"🔑 Password provided: {'✅ Yes' if password else '❌ No'}")
        
        # Step 1: Basic validation
        if not username or not password:
            print("❌ BACKEND: Missing username or password")
            print("="*80)
            return None
        
        # Step 2: Skip if this looks like admin login (contains @ or too short)
        if '@' in username or (len(username) < 3 and not username.isdigit()):
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
        
        # Step 4: Find facility by credential number
        try:
            # Try exact match first
            facility = Facility.objects.filter(credential_number=username).first()
            
            if not facility and username.isdigit():
                # If username is just digits, try finding by prefix (registration number)
                facility = Facility.objects.filter(
                    credential_number__startswith=f"{username}-AGC"
                ).first()
            
            if not facility:
                print(f"❌ BACKEND: Facility not found for credential '{username}'")
                self._log_failed_attempt(request, username, 'facility_not_found')
                print("="*80)
                return None
            
            print(f"✅ BACKEND: Found facility {facility.name}")
            print(f"   🆔 Credential Number: {facility.credential_number}")
            
            # Step 5: Check if facility is active
            if facility.status != 'active':
                print(f"❌ BACKEND: Facility not active ({facility.status})")
                self._log_failed_attempt(request, username, f'facility_status_{facility.status}')
                print("="*80)
                return None
            
            print("✅ BACKEND: Facility is active")
            
        except Exception as e:
            print(f"❌ BACKEND: Database error: {str(e)}")
            self._log_failed_attempt(request, username, f'database_error_{str(e)}')
            print("="*80)
            return None
        
        # Step 6: Create/get user using full credential number as username
        try:
            user = self._get_or_create_facility_user(facility)
            if user:
                print(f"✅ BACKEND SUCCESS: {user.username}")
                self._log_successful_attempt(request, username, facility)
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
        
        # Use full credential number as username
        username = facility.credential_number
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
            
            # Create email using credential number (safe for email)
            safe_credential = facility.credential_number.replace('-', '_')
            
            user = User.objects.create_user(
                username=username,
                password='bestfit#123',
                first_name=first_name,
                last_name=last_name,
                email=f"{safe_credential}@facility.bestfit.com",
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
    
    def _log_successful_attempt(self, request, username, facility):
        """Log successful login attempt"""
        try:
            registration_number = facility.get_registration_number() if hasattr(facility, 'get_registration_number') else username
            
            LoginAttempt.objects.create(
                username=username,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                attempt_type='success',
                registration_number=registration_number,
                credential_number=facility.credential_number
            )
        except Exception as e:
            print(f"   ⚠️  Could not log success: {str(e)}")
    
    def _log_failed_attempt(self, request, username, reason):
        """Log failed login attempt"""
        try:
            # Extract registration number if possible
            registration_number = username
            if '-AGC' in username:
                registration_number = username.split('-AGC')[0]
            
            LoginAttempt.objects.create(
                username=username,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                attempt_type='failure',
                failure_reason=reason,
                registration_number=registration_number if registration_number.isdigit() else None,
                credential_number=username if '-AGC' in username else None
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
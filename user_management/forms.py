# user_management/forms.py - Updated for credential number system

from django import forms
from django.contrib.auth import authenticate
from search.models import Facility
import logging

logger = logging.getLogger(__name__)

class CustomLoginForm(forms.Form):
    """
    COMPLETELY CUSTOM login form that doesn't inherit from AuthenticationForm
    This prevents Django's default validation from interfering
    """
    
    LOGIN_TYPES = [
        ('admin', 'Search Engine Administrator'),
        ('facility', 'Facility Staff'),
    ]
    
    login_type = forms.ChoiceField(
        choices=LOGIN_TYPES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='admin'
    )
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Registration Number (4-5 digits)'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    def __init__(self, request=None, *args, **kwargs):
        """Initialize form with request"""
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
    
    def clean(self):
        """Custom validation with proper status message handling"""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        login_type = cleaned_data.get('login_type')
        
        print("\n" + "="*80)
        print("📝 CUSTOM FORM VALIDATION STARTED")
        print("="*80)
        print(f"🔐 Login Type: {login_type}")
        print(f"👤 Username: '{username}'")
        print(f"🔑 Password: {'[PROVIDED]' if password else '[MISSING]'}")
        
        if not username or not password:
            print("❌ FORM ERROR: Username or password missing")
            print("="*80)
            raise forms.ValidationError("Please provide both username and password.")
        
        if login_type == 'facility':
            print("\n🏥 FACILITY STAFF LOGIN VALIDATION")
            print("-" * 40)
            
            # Step 1: Find facility by registration number (first 4-5 digits)
            print(f"🔍 Looking for facility with registration number: '{username}'")
            
            # Validate registration number format (4-5 digits)
            if not username.isdigit() or len(username) not in [4, 5]:
                print(f"❌ INVALID REGISTRATION FORMAT: {username}")
                error_msg = "Registration number must be 4-5 digits only. Please verify and try again."
                print(f"   📧 Error message: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            try:
                # Find facility where credential number starts with the registration number
                facility = Facility.objects.filter(
                    credential_number__startswith=f"{username}-AGC"
                ).first()
                
                if not facility:
                    # Also try finding by exact credential number match (for simple number format)
                    facility = Facility.objects.filter(credential_number=username).first()
                
                if not facility:
                    print(f"❌ FACILITY NOT FOUND: {username}")
                    error_msg = "No facility found with this registration number. Please verify the number and try again."
                    print(f"   📧 Error message: {error_msg}")
                    print("="*80)
                    raise forms.ValidationError(error_msg)
                
                print(f"✅ FACILITY FOUND:")
                print(f"   📋 Name: {facility.name}")
                print(f"   🆔 Credential Number: {facility.credential_number}")
                print(f"   📊 Status: {facility.status}")
                print(f"   📍 Location: {facility.state}, {facility.county}")
                
            except Exception as e:
                print(f"❌ DATABASE ERROR: {str(e)}")
                error_msg = "System error while looking up facility. Please try again or contact support."
                print(f"   📧 Error message: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            # Step 2: Check facility status with detailed messages
            if facility.status != 'active':
                print(f"❌ FACILITY NOT ACTIVE: Status = {facility.status}")
                
                # Detailed status messages
                status_messages = {
                    'pending': 'Your facility registration is currently pending approval. Please wait for activation or contact support for assistance.',
                    'inactive': 'Your facility has been temporarily deactivated. Please contact support to reactivate your account.',
                    'rejected': 'Your facility application was not approved. Please contact support with correct information to resubmit.',
                    'draft': 'Your facility registration is incomplete. Please complete the registration process or contact support.',
                    'suspended': 'Your facility account has been suspended. Please contact support to resolve this issue.',
                    'under_review': 'Your facility is currently under review. Please wait for the review process to complete.'
                }
                
                error_msg = status_messages.get(
                    facility.status, 
                    f'Your facility status is "{facility.get_status_display()}". Please contact support for assistance.'
                )
                
                print(f"   📧 Status message: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            # Step 3: Check password
            if password != 'bestfit#123':
                print(f"❌ WRONG PASSWORD for facility {facility.name}")
                error_msg = "Incorrect password. Please use 'bestfit#123' for facility staff login."
                print(f"   📧 Password error: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            print("✅ All facility validations passed - attempting authentication")
            
            # Step 4: Try authentication using the full credential number as username
            user = authenticate(
                request=self.request,
                username=facility.credential_number,  # Use full credential for auth
                password=password
            )
            
            if user is None:
                print(f"❌ AUTHENTICATION FAILED for facility {facility.name}")
                error_msg = "Authentication system error. Please contact support if this continues."
                print(f"   📧 Auth error: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            if not user.is_active:
                print(f"❌ USER ACCOUNT INACTIVE for {user.username}")
                error_msg = "Your account has been deactivated. Please contact support."
                print(f"   📧 Account error: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            print(f"✅ FACILITY AUTHENTICATION SUCCESSFUL: {user.username}")
            # Store the facility object for later use
            user.associated_facility = facility
            self.user_cache = user
        
        else:
            # Admin login handling
            print("\n👨‍💼 ADMIN LOGIN VALIDATION")
            print("-" * 40)
            
            user = authenticate(
                request=self.request,
                username=username,
                password=password
            )
            
            if user is None:
                print(f"❌ ADMIN AUTHENTICATION FAILED for: {username}")
                error_msg = "Invalid admin username or password."
                print(f"   📧 Admin error: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            if not user.is_active:
                print(f"❌ ADMIN ACCOUNT INACTIVE: {username}")
                error_msg = "This admin account has been deactivated."
                print(f"   📧 Admin inactive: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            # Check admin permissions
            is_admin = (user.is_staff or user.is_superuser or 
                       (hasattr(user, 'user_profile') and 
                        user.user_profile.user_type in ['super_admin', 'search_admin']))
            
            if not is_admin:
                print(f"❌ INSUFFICIENT ADMIN PRIVILEGES: {username}")
                error_msg = "You don't have administrator access privileges."
                print(f"   📧 Permission error: {error_msg}")
                print("="*80)
                raise forms.ValidationError(error_msg)
            
            print(f"✅ ADMIN AUTHENTICATION SUCCESSFUL: {username}")
            self.user_cache = user
        
        print("="*80)
        return cleaned_data
    
    def get_user(self):
        """Return the authenticated user"""
        return self.user_cache


class StaffFacilityForm(forms.ModelForm):
    """
    Clean form for facility staff that only includes editable fields
    Completely excludes: credential_number, bed_count, facility_type
    """
    
    class Meta:
        model = Facility
        fields = [
            'name',
            'endorsement',
            'address',
            'state',
            'county',
            'contact',
            'contact_person',
            'image',
            'meta_description',
            'search_keywords'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter facility name'
            }),
            'endorsement': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter endorsement/specialization'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter complete facility address'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter state'
            }),
            'county': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter county'
            }),
            'contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(555) 123-4567'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter contact person name'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': 160,
                'placeholder': 'Brief description of your facility for search results (max 160 characters)'
            }),
            'search_keywords': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter keywords separated by commas (e.g., skilled nursing, rehabilitation, memory care)'
            })
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set required fields
        self.fields['name'].required = True
        self.fields['address'].required = True
        self.fields['state'].required = True
        self.fields['county'].required = True
        
        # Add help text
        self.fields['meta_description'].help_text = "This description appears in search results. Keep it clear and informative."
        self.fields['search_keywords'].help_text = "Keywords help patients find your facility. Include services, specialties, and location terms."
        self.fields['endorsement'].help_text = "Enter any specializations or endorsements your facility has."
    
    def clean_meta_description(self):
        """Validate meta description length"""
        meta_description = self.cleaned_data.get('meta_description')
        if meta_description and len(meta_description) > 160:
            raise forms.ValidationError("Description must be 160 characters or less.")
        return meta_description
    
    def clean_contact(self):
        """Validate contact phone number format"""
        contact = self.cleaned_data.get('contact')
        if contact:
            # Remove non-digit characters for validation
            digits_only = ''.join(filter(str.isdigit, contact))
            if len(digits_only) < 10:
                raise forms.ValidationError("Please enter a valid phone number with at least 10 digits.")
        return contact
# user_management/views.py - Enhanced version with bed management removed

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.generic import FormView
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.models import User
import json

from .forms import CustomLoginForm
from .models import UserSession, LoginAttempt, UserProfile
from search.models import Facility
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

import logging

logger = logging.getLogger(__name__)
from search.models import FacilityPricing
from search.forms import FacilityPricingForm

class CustomLoginView(FormView):
    """
    Enhanced custom login view using FormView instead of LoginView
    This gives us complete control over the process with improved error handling
    """
    
    form_class = CustomLoginForm
    template_name = 'user_management/login.html'
    
    def get_form_kwargs(self):
        """Pass request to form"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        """Handle successful form validation with enhanced logging and session management"""
        login_type = form.cleaned_data.get('login_type')
        user = form.get_user()
        
        print("\n" + "="*80)
        print("✅ FORM VALIDATION SUCCESSFUL - LOGGING IN USER")
        print("="*80)
        print(f"🔐 Login Type: {login_type}")
        print(f"👤 User: {user.username}")
        print(f"📧 Email: {user.email}")
        print(f"🕒 Login Time: {timezone.now()}")
        
        # Record login attempt
        self._record_login_attempt(user, success=True)
        
        # Login the user
        login(self.request, user)
        print("✅ User logged in successfully")
        
        # Create enhanced session record
        self._create_session_record(user)
        
        # Update user's last login info
        self._update_user_login_info(user)
        
        # Set success message based on login type
        self._set_welcome_message(user, login_type)
        
        # Redirect to appropriate dashboard
        redirect_url = self.get_success_url(user, login_type)
        print(f"🎯 Redirecting to: {redirect_url}")
        print("="*80)
        
        return redirect(redirect_url)
    
    def form_invalid(self, form):
        """Handle form validation errors with enhanced logging"""
        print("\n" + "="*80)
        print("❌ FORM VALIDATION FAILED")
        print("="*80)
        print(f"📝 Form Errors: {form.errors}")
        print(f"🕒 Failed Login Time: {timezone.now()}")
        
        # Record failed login attempt
        username = form.data.get('username', 'unknown')
        self._record_login_attempt(username=username, success=False)
        
        # Enhanced error logging
        logger.warning(f"Failed login attempt for username: {username} from IP: {self._get_client_ip()}")
        
        print("🔄 Returning to login form with custom error messages")
        print("="*80)
        
        return super().form_invalid(form)
    
    def get_success_url(self, user, login_type):
        """Enhanced redirect URL determination based on user type and permissions"""
        print(f"🧭 Determining redirect for user: {user.username}, type: {login_type}")
        
        if login_type == 'facility':
            # Check if user has facility access
            if hasattr(user, 'user_profile') and user.user_profile.facility:
                return reverse('user_management:facility_dashboard')
            else:
                messages.warning(self.request, "No facility associated with your account. Please contact administrator.")
                return reverse('search:home')
        elif user.is_staff or user.is_superuser:
            # Try facility admin first, then fallback to Django admin
            try:
                return reverse('facility_admin:dashboard')
            except:
                return '/admin/'
        else:
            # Regular users go to search home
            return reverse('search:home')
    
    def _record_login_attempt(self, user=None, username=None, success=True):
        """Record login attempt for security auditing"""
        try:
            attempt_data = {
                'ip_address': self._get_client_ip(),
                'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
                'success': success,
                'timestamp': timezone.now(),
                'device_type': self._detect_device_type(),
                'browser': self._detect_browser()
            }
            
            if user:
                attempt_data['user'] = user
            elif username:
                attempt_data['username'] = username
            
            LoginAttempt.objects.create(**attempt_data)
            print(f"📊 Login attempt recorded: {'SUCCESS' if success else 'FAILED'}")
        except Exception as e:
            logger.error(f"Failed to record login attempt: {str(e)}")
    
    def _create_session_record(self, user):
        """Create enhanced session tracking record"""
        try:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            
            # Clean up old sessions for this user (optional security feature)
            UserSession.objects.filter(user=user, is_active=False).delete()
            
            session_record = UserSession.objects.create(
                user=user,
                session_key=session_key,
                ip_address=self._get_client_ip(),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                device_type=self._detect_device_type(),
                browser=self._detect_browser(),
                login_time=timezone.now(),
                is_active=True
            )
            
            # Store session info in Django session for quick access
            self.request.session['user_session_id'] = session_record.id
            self.request.session['login_time'] = timezone.now().isoformat()
            
            print("✅ Enhanced session record created")
        except Exception as e:
            logger.error(f"Failed to create session record: {str(e)}")
            print(f"⚠️  Failed to create session record: {str(e)}")
    
    def _update_user_login_info(self, user):
        """Update user's last login information"""
        try:
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Update user profile if exists
            if hasattr(user, 'user_profile'):
                profile = user.user_profile
                profile.last_login_ip = self._get_client_ip()
                profile.last_login_device = self._detect_device_type()
                profile.save(update_fields=['last_login_ip', 'last_login_device'])
            
            print("✅ User login info updated")
        except Exception as e:
            logger.error(f"Failed to update user login info: {str(e)}")
    
    def _set_welcome_message(self, user, login_type):
        """Set personalized welcome message"""
        if login_type == 'facility':
            if hasattr(user, 'user_profile') and user.user_profile.facility:
                facility_name = user.user_profile.facility.name
                message = f"Welcome back to {facility_name}! You have successfully accessed your facility dashboard."
                print(f"🎉 Facility welcome: {facility_name}")
            else:
                message = "Welcome! Successfully logged into facility dashboard."
                print(f"🎉 Generic facility welcome")
            messages.success(self.request, message)
        else:
            if user.first_name:
                message = f"Welcome back, {user.first_name}! You have successfully logged into the admin portal."
            else:
                message = "Welcome to the admin portal!"
            print(f"🎉 Admin welcome")
            messages.success(self.request, message)
    
    def _get_client_ip(self):
        """Get client IP address with improved detection"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip
    
    def _detect_device_type(self):
        """Enhanced device type detection"""
        user_agent = self.request.META.get('HTTP_USER_AGENT', '').lower()
        if any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone']):
            return 'mobile'
        elif any(tablet in user_agent for tablet in ['tablet', 'ipad']):
            return 'tablet'
        else:
            return 'desktop'
    
    def _detect_browser(self):
        """Enhanced browser detection"""
        user_agent = self.request.META.get('HTTP_USER_AGENT', '').lower()
        if 'edg' in user_agent:  # Edge uses 'edg' in user agent
            return 'edge'
        elif 'chrome' in user_agent and 'safari' in user_agent:
            return 'chrome'
        elif 'firefox' in user_agent:
            return 'firefox'
        elif 'safari' in user_agent and 'chrome' not in user_agent:
            return 'safari'
        elif 'opera' in user_agent or 'opr' in user_agent:
            return 'opera'
        else:
            return 'unknown'


@login_required
def facility_dashboard(request):
    """Enhanced facility dashboard view with bed management status integration"""
    
    print(f"\n🏥 FACILITY DASHBOARD ACCESS: {request.user.username}")
    print(f"🕒 Access Time: {timezone.now()}")
    
    # Enhanced user type checking
    try:
        user_profile = request.user.user_profile
        if user_profile.user_type != 'facility_staff':
            messages.error(request, "Access denied - facility staff access required.")
            logger.warning(f"Non-facility user {request.user.username} attempted to access facility dashboard")
            return redirect('search:home')
    except AttributeError:
        messages.error(request, "User profile not found. Please contact administrator.")
        return redirect('search:home')
    
    # Get facility with error handling
    facility = user_profile.facility
    if not facility:
        messages.error(request, "No facility associated with your account. Please contact administrator.")
        return redirect('search:home')
    
    # Enhanced facility status checking
    if facility.status != 'active':
        messages.error(request, f"Facility access suspended. Status: {facility.get_status_display()}. Please contact administrator.")
        logger.warning(f"User {request.user.username} attempted to access inactive facility: {facility.name}")
        logout(request)
        return redirect('user_management:login')
    
    # Get bed management status from bedupdates app
    bed_config = None
    bed_stats = None
    rooms = None
    
    try:
        from bedupdates.models import FacilityConfiguration, Room
        
        # Get bed configuration status
        try:
            bed_config = FacilityConfiguration.objects.get(facility=facility)
            
            if bed_config.is_configured:
                # Get rooms and calculate statistics
                rooms = Room.objects.filter(facility_config=bed_config, is_active=True).prefetch_related('beds')
                
                total_beds = sum(room.get_total_beds() for room in rooms)
                occupied_beds = sum(room.get_occupied_beds() for room in rooms)
                vacant_beds = total_beds - occupied_beds
                
                bed_stats = {
                    'total_beds': total_beds,
                    'occupied_beds': occupied_beds,
                    'vacant_beds': vacant_beds,
                    'occupancy_rate': (occupied_beds / total_beds * 100) if total_beds > 0 else 0
                }
                
                # Calculate room statistics
                room_stats = {
                    'private_rooms': rooms.filter(room_type='private').count(),
                    'shared_rooms': rooms.filter(room_type='shared').count(),
                }
            else:
                # Configuration exists but not completed
                bed_stats = None
                room_stats = None
                
        except FacilityConfiguration.DoesNotExist:
            # No configuration exists yet
            bed_config = None
            bed_stats = None
            room_stats = None
            
    except ImportError:
        logger.warning("BedUpdate models not available")
        bed_config = None
        bed_stats = None
        room_stats = None
    
    # Fallback to legacy bed counting if advanced system not configured
    if not bed_config or not bed_config.is_configured:
        try:
            from bedupdates.models import BedAvailability
            bed_data = BedAvailability.objects.filter(facility=facility).first()
            
            # Calculate legacy bed statistics
            total_beds = facility.bed_count or 0
            available_beds = bed_data.available_beds if bed_data else 0
            occupied_beds = max(0, total_beds - available_beds)
            occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
            
            # Create legacy bed stats for template consistency
            if not bed_stats:
                bed_stats = {
                    'total_beds': total_beds,
                    'occupied_beds': occupied_beds,
                    'vacant_beds': available_beds,
                    'occupancy_rate': occupancy_rate
                }
        except ImportError:
            # If even legacy system not available
            bed_stats = {
                'total_beds': facility.bed_count or 0,
                'occupied_beds': 0,
                'vacant_beds': facility.bed_count or 0,
                'occupancy_rate': 0
            }
    
    # Get landing page status (if available)
    landing_page = None
    try:
        from facility_landing.models import FacilityLandingPage
        landing_page = FacilityLandingPage.objects.filter(facility=facility).first()
    except ImportError:
        pass
    
    # Get recent session info
    recent_sessions = UserSession.objects.filter(
        user=request.user
    ).order_by('-login_time')[:5]
    
    context = {
        'facility': facility,
        'user': request.user,
        'user_profile': user_profile,
        'recent_sessions': recent_sessions,
        
        # Bed management data from bedupdates app
        'bed_config': bed_config,
        'bed_stats': bed_stats,
        'rooms': rooms[:3] if rooms else None,  # Preview first 3 rooms
        'room_stats': locals().get('room_stats'),
        
        # Landing page data
        'landing_page': landing_page,
        
        # Legacy fallback values for template compatibility
        'total_beds': bed_stats.get('total_beds', 0) if bed_stats else 0,
        'available_beds': bed_stats.get('vacant_beds', 0) if bed_stats else 0,
        'occupied_beds': bed_stats.get('occupied_beds', 0) if bed_stats else 0,
        'occupancy_rate': round(bed_stats.get('occupancy_rate', 0), 1) if bed_stats else 0,
    }
    
    return render(request, 'user_management/facility_dashboard.html', context)


@login_required
def facility_pricing_management(request):
    """Facility staff pricing management view"""
    
    print(f"\n💰 FACILITY PRICING MANAGEMENT ACCESS: {request.user.username}")
    print(f"🕒 Access Time: {timezone.now()}")
    
    # Enhanced user type checking
    try:
        user_profile = request.user.user_profile
        if user_profile.user_type != 'facility_staff':
            messages.error(request, "Access denied - facility staff access required.")
            logger.warning(f"Non-facility user {request.user.username} attempted to access pricing management")
            return redirect('search:home')
    except AttributeError:
        messages.error(request, "User profile not found. Please contact administrator.")
        return redirect('search:home')
    
    # Get facility with error handling
    facility = user_profile.facility
    if not facility:
        messages.error(request, "No facility associated with your account. Please contact administrator.")
        return redirect('search:home')
    
    # Enhanced facility status checking
    if facility.status not in ['active', 'pending']:
        messages.error(request, f"Pricing management not allowed. Status: {facility.get_status_display()}. Please contact administrator.")
        return redirect('user_management:facility_dashboard')
    
    # Get or create pricing instance
    pricing, created = FacilityPricing.objects.get_or_create(
        facility=facility,
        defaults={'updated_by': request.user}
    )
    
    if created:
        logger.info(f"Created new pricing record for facility: {facility.name}")
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                form = FacilityPricingForm(request.POST, instance=pricing)
                
                if form.is_valid():
                    pricing = form.save(commit=False)
                    pricing.updated_by = request.user
                    pricing.save()
                    
                    # Log the pricing update
                    logger.info(f"Pricing updated for facility {facility.name} by {request.user.username}")
                    
                    messages.success(
                        request, 
                        "Pricing information updated successfully! "
                        "Your updated pricing will now be visible to potential residents."
                    )
                    
                    # Redirect back to pricing management to prevent re-submission
                    return redirect('user_management:facility_pricing_management')
                else:
                    messages.error(request, "Please correct the errors in the form below.")
                    logger.warning(f"Form validation failed for pricing update: {form.errors}")
                    
        except Exception as e:
            logger.error(f"Error updating pricing for facility {facility.name}: {str(e)}")
            messages.error(request, "An error occurred while updating pricing information. Please try again.")
    else:
        form = FacilityPricingForm(instance=pricing)
    
    # Calculate some stats for display
    context = {
        'form': form,
        'facility': facility,
        'pricing': pricing,
        'user_profile': user_profile,
        'title': f'Pricing Management - {facility.name}',
        'has_pricing_info': pricing.has_pricing_info,
        'private_display': pricing.private_bed_display,
        'shared_display': pricing.shared_bed_display,
    }
    
    return render(request, 'user_management/facility_pricing_management.html', context)


@login_required
def facility_pricing_preview(request):
    """Preview how pricing appears to public"""
    
    # Enhanced user type checking
    try:
        user_profile = request.user.user_profile
        if user_profile.user_type != 'facility_staff':
            messages.error(request, "Access denied - facility staff access required.")
            return redirect('search:home')
    except AttributeError:
        messages.error(request, "User profile not found. Please contact administrator.")
        return redirect('search:home')
    
    # Get facility
    facility = user_profile.facility
    if not facility:
        messages.error(request, "No facility associated with your account.")
        return redirect('search:home')
    
    # Get pricing info
    try:
        pricing = facility.pricing
    except FacilityPricing.DoesNotExist:
        pricing = None
    
    context = {
        'facility': facility,
        'pricing': pricing,
        'is_preview': True,
    }
    
    return render(request, 'user_management/facility_pricing_preview.html', context)


@login_required
def user_profile(request):
    """Enhanced user profile view with improved validation and features"""
    
    user_profile = getattr(request.user, 'user_profile', None)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                user = request.user
                
                # Validate and update user fields
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                email = request.POST.get('email', '').strip()
                
                # Basic validation
                if email and User.objects.filter(email=email).exclude(id=user.id).exists():
                    messages.error(request, "This email address is already in use by another user.")
                    return redirect('user_management:profile')
                
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                
                # Update user profile if exists
                if user_profile:
                    user_profile.phone_number = request.POST.get('phone_number', '').strip()
                    user_profile.job_title = request.POST.get('job_title', '').strip()
                    user_profile.bio = request.POST.get('bio', '').strip()
                    user_profile.save()
                
                # Log the profile update
                logger.info(f"Profile updated for user {user.username}")
                
                messages.success(request, "Profile updated successfully!")
                return redirect('user_management:profile')
                
        except ValidationError as e:
            messages.error(request, f"Validation error: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating profile for user {request.user.username}: {str(e)}")
            messages.error(request, "An error occurred while updating your profile. Please try again.")
    
    # Get user's recent activity
    recent_sessions = UserSession.objects.filter(
        user=request.user
    ).order_by('-login_time')[:10]
    
    context = {
        'user': request.user,
        'profile': user_profile,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'user_management/profile.html', context)


def custom_logout(request):
    """Enhanced custom logout with session cleanup"""
    if request.user.is_authenticated:
        try:
            # Mark user session as inactive
            session_id = request.session.get('user_session_id')
            if session_id:
                UserSession.objects.filter(id=session_id).update(
                    is_active=False,
                    logout_time=timezone.now()
                )
            
            # Log the logout
            logger.info(f"User {request.user.username} logged out")
            
            messages.success(request, "You have been successfully logged out. Thank you for using our system!")
        except Exception as e:
            logger.error(f"Error during logout for user {request.user.username}: {str(e)}")
            messages.success(request, "You have been logged out.")
    
    logout(request)
    return redirect('search:home')


@require_http_methods(["GET"])
def validate_facility_api(request):
    """Enhanced API to validate facility with additional information"""
    registration_number = request.GET.get('registration_number')  # Changed from inspection_number
    if not registration_number:
        return JsonResponse({'error': 'Registration number required'}, status=400)
    
    try:
        # Use the new credential number system
        facility = Facility.objects.filter(
            credential_number__startswith=f"{registration_number}-AGC"
        ).first()
        
        if not facility:
            # Also try exact match for simple format
            facility = Facility.objects.filter(credential_number=registration_number).first()
        
        if not facility:
            return JsonResponse({'valid': False, 'error': 'Facility not found'}, status=404)
        
        # Get bed information from bedupdates app
        bed_info = None
        try:
            from bedupdates.models import FacilityConfiguration, BedAvailability
            
            # Try advanced system first
            config = FacilityConfiguration.objects.filter(facility=facility).first()
            if config and config.is_configured:
                from bedupdates.models import Room
                rooms = Room.objects.filter(facility_config=config, is_active=True)
                total_beds = sum(room.get_total_beds() for room in rooms)
                available_beds = sum(room.get_vacant_beds() for room in rooms)
                
                bed_info = {
                    'total_beds': total_beds,
                    'available_beds': available_beds,
                    'system_type': 'advanced',
                    'last_updated': config.updated_at.isoformat() if config.updated_at else None
                }
            else:
                # Fallback to legacy system
                bed_data = BedAvailability.objects.filter(facility=facility).first()
                if bed_data:
                    bed_info = {
                        'total_beds': facility.bed_count,
                        'available_beds': bed_data.available_beds,
                        'system_type': 'legacy',
                        'last_updated': bed_data.updated_at.isoformat() if bed_data.updated_at else None
                    }
        except ImportError:
            pass
        
        response_data = {
            'valid': True,
            'facility_name': facility.name,
            'facility_type': facility.facility_type,
            'state': facility.state,
            'county': facility.county,
            'status': facility.status,
            'is_active': facility.status == 'active',
            'bed_info': bed_info,
            'contact_info': {
                'phone': facility.contact,
                'contact_person': facility.contact_person,
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error validating facility {registration_number}: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def update_session_activity(request):
    """API endpoint to update user session activity (for keeping sessions alive)"""
    try:
        session_id = request.session.get('user_session_id')
        if session_id:
            UserSession.objects.filter(id=session_id).update(
                last_activity=timezone.now()
            )
            return JsonResponse({'status': 'success'})
        return JsonResponse({'error': 'No active session found'}, status=400)
    except Exception as e:
        logger.error(f"Error updating session activity: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def user_sessions(request):
    """View to show user's active sessions (security feature)"""
    sessions = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-login_time')
    
    context = {
        'sessions': sessions,
        'current_session_id': request.session.get('user_session_id'),
    }
    
    return render(request, 'user_management/user_sessions.html', context)


@login_required
@require_http_methods(["POST"])
def terminate_session(request, session_id):
    """Terminate a specific user session"""
    try:
        session = UserSession.objects.get(
            id=session_id,
            user=request.user
        )
        session.is_active = False
        session.logout_time = timezone.now()
        session.save()
        
        messages.success(request, "Session terminated successfully.")
        logger.info(f"User {request.user.username} terminated session {session_id}")
        
    except UserSession.DoesNotExist:
        messages.error(request, "Session not found.")
    except Exception as e:
        logger.error(f"Error terminating session {session_id}: {str(e)}")
        messages.error(request, "Error terminating session.")
    
    return redirect('user_management:user_sessions')


@login_required
def facility_detail_staff(request):
    """Staff view of their facility details with change history"""
    
    print(f"\n🏥 FACILITY DETAIL ACCESS: {request.user.username}")
    print(f"🕒 Access Time: {timezone.now()}")
    
    # Enhanced user type checking
    try:
        user_profile = request.user.user_profile
        if user_profile.user_type != 'facility_staff':
            messages.error(request, "Access denied - facility staff access required.")
            logger.warning(f"Non-facility user {request.user.username} attempted to access facility details")
            return redirect('search:home')
    except AttributeError:
        messages.error(request, "User profile not found. Please contact administrator.")
        return redirect('search:home')
    
    # Get facility with error handling
    facility = user_profile.facility
    if not facility:
        messages.error(request, "No facility associated with your account. Please contact administrator.")
        return redirect('search:home')
    
    # Enhanced facility status checking
    if facility.status != 'active':
        messages.warning(request, f"Facility status: {facility.get_status_display()}. Some information may be limited.")
    
    # Get change history (if available)
    change_logs = []
    try:
        from search.models import FacilityChangeLog
        change_logs = FacilityChangeLog.objects.filter(facility=facility).order_by('-timestamp')[:10]
    except ImportError:
        logger.warning("FacilityChangeLog model not available")
    
    # Get submission details (if available)
    submission = None
    try:
        from search.models import FacilitySubmission
        submission = getattr(facility, 'facilitysubmission', None)
    except ImportError:
        pass
    
    # Get bed management status from bedupdates app (no bed updates in user_management)
    bed_config = None
    try:
        from bedupdates.models import FacilityConfiguration
        bed_config = FacilityConfiguration.objects.filter(facility=facility).first()
    except ImportError:
        pass
    
    context = {
        'facility': facility,
        'user_profile': user_profile,
        'change_logs': change_logs,
        'submission': submission,
        'bed_config': bed_config,  # For display only
        'can_edit': True,  # Staff can request edits
    }
    
    return render(request, 'user_management/facility_detail_staff.html', context)

@login_required
def facility_update_staff(request):
    """Staff form to update their facility information"""
    
    print(f"\n🏥 FACILITY UPDATE ACCESS: {request.user.username}")
    print(f"🕒 Access Time: {timezone.now()}")
    
    # Enhanced user type checking
    try:
        user_profile = request.user.user_profile
        if user_profile.user_type != 'facility_staff':
            messages.error(request, "Access denied - facility staff access required.")
            logger.warning(f"Non-facility user {request.user.username} attempted to access facility update")
            return redirect('search:home')
    except AttributeError:
        messages.error(request, "User profile not found. Please contact administrator.")
        return redirect('search:home')
    
    # Get facility with error handling
    facility = user_profile.facility
    if not facility:
        messages.error(request, "No facility associated with your account. Please contact administrator.")
        return redirect('search:home')
    
    # Enhanced facility status checking
    if facility.status not in ['active', 'pending']:
        messages.error(request, f"Facility updates not allowed. Status: {facility.get_status_display()}. Please contact administrator.")
        return redirect('user_management:facility_dashboard')
    
    # Import the custom staff form that excludes readonly fields
    try:
        from .forms import StaffFacilityForm
    except ImportError:
        messages.error(request, "Facility update form not available. Please contact administrator.")
        return redirect('user_management:facility_dashboard')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Store old values for change tracking
                old_values = {
                    'name': facility.name,
                    'facility_type': facility.facility_type,
                    'endorsement': facility.endorsement,
                    'address': facility.address,
                    'state': facility.state,
                    'county': facility.county,
                    'contact': facility.contact,
                    'contact_person': facility.contact_person,
                    'meta_description': facility.meta_description,
                    'search_keywords': facility.search_keywords,
                }
                
                # Create form with POST data - using custom staff form
                form = StaffFacilityForm(request.POST, request.FILES, instance=facility)
                
                if form.is_valid():
                    # Save the form - readonly fields won't be affected since they're not in the form
                    updated_facility = form.save()
                    
                    # The credential_number and bed_count remain unchanged automatically
                    # since they're not included in the form
                    
                    # Log the changes
                    try:
                        from search.models import FacilityChangeLog
                        new_values = {
                            'name': updated_facility.name,
                            'facility_type': updated_facility.facility_type,
                            'endorsement': updated_facility.endorsement,
                            'address': updated_facility.address,
                            'state': updated_facility.state,
                            'county': updated_facility.county,
                            'contact': updated_facility.contact,
                            'contact_person': updated_facility.contact_person,
                            'meta_description': updated_facility.meta_description,
                            'search_keywords': updated_facility.search_keywords,
                        }
                        
                        FacilityChangeLog.objects.create(
                            facility=updated_facility,
                            changed_by=request.user,
                            change_type='updated_by_staff',
                            old_values=old_values,
                            new_values=new_values,
                            notes=f'Updated by facility staff: {request.user.username}'
                        )
                    except ImportError:
                        logger.warning("FacilityChangeLog model not available")
                    
                    logger.info(f"Facility {facility.name} updated by staff user {request.user.username}")
                    messages.success(request, "Facility information updated successfully!")
                    return redirect('user_management:facility_detail_staff')
                else:
                    messages.error(request, "Please correct the errors in the form below.")
                    print(f"Form validation errors: {form.errors}")
                    
        except Exception as e:
            logger.error(f"Error updating facility for user {request.user.username}: {str(e)}")
            messages.error(request, "An error occurred while updating facility information. Please try again.")
    else:
        form = StaffFacilityForm(instance=facility)
        print(f"🔍 Current facility type: '{facility.facility_type}'")
    
    context = {
        'form': form,
        'facility': facility,
        'user_profile': user_profile,
        'title': f'Update {facility.name}',
        'submit_text': 'Update Facility Information',
        'is_staff_update': True,
    }
    
    return render(request, 'user_management/facility_update_staff.html', context)
# user_management/views.py - Enhanced version with all previous features + improvements

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

logger = logging.getLogger(__name__)

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
    """Enhanced facility dashboard view with improved error handling and features"""
    
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
    
    # Handle bed updates with enhanced error handling
    bed_data = None
    bed_form = None
    bed_update_success = False
    
    try:
        from bedupdates.models import BedAvailability
        from bedupdates.forms import BedAvailabilityForm
        
        bed_data, created = BedAvailability.objects.get_or_create(facility=facility)
        
        if request.method == 'POST':
            bed_form = BedAvailabilityForm(request.POST, instance=bed_data)
            if bed_form.is_valid():
                with transaction.atomic():
                    bed_update = bed_form.save(commit=False)
                    bed_update.updated_by = request.user
                    bed_update.updated_at = timezone.now()
                    bed_update.save()
                    
                    # Log the bed update
                    logger.info(f"Bed availability updated by {request.user.username} for facility {facility.name}")
                    
                bed_update_success = True
                messages.success(request, "Bed availability updated successfully!")
                return redirect('user_management:facility_dashboard')
            else:
                messages.error(request, "Please correct the errors in the bed availability form.")
        else:
            bed_form = BedAvailabilityForm(instance=bed_data)
            
    except ImportError:
        logger.warning("BedAvailability models not available")
        messages.warning(request, "Bed management features are currently unavailable.")
    except Exception as e:
        logger.error(f"Error handling bed updates: {str(e)}")
        messages.error(request, "An error occurred while processing bed information.")
    
    # Calculate bed statistics
    total_beds = facility.bed_count or 0
    available_beds = bed_data.available_beds if bed_data else 0
    occupied_beds = max(0, total_beds - available_beds)
    occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
    
    # Get recent session info
    recent_sessions = UserSession.objects.filter(
        user=request.user
    ).order_by('-login_time')[:5]
    
    context = {
        'facility': facility,
        'bed_data': bed_data,
        'bed_form': bed_form,
        'total_beds': total_beds,
        'available_beds': available_beds,
        'occupied_beds': occupied_beds,
        'occupancy_rate': round(occupancy_rate, 1),
        'user': request.user,
        'user_profile': user_profile,
        'recent_sessions': recent_sessions,
        'last_bed_update': bed_data.updated_at if bed_data else None,
        'bed_update_success': bed_update_success,
    }
    
    return render(request, 'user_management/facility_dashboard.html', context)


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
    inspection_number = request.GET.get('inspection_number')
    if not inspection_number:
        return JsonResponse({'error': 'Inspection number required'}, status=400)
    
    try:
        facility = Facility.objects.get(inspection_number=inspection_number)
        
        # Get additional facility information
        bed_info = None
        try:
            from bedupdates.models import BedAvailability
            bed_data = BedAvailability.objects.filter(facility=facility).first()
            if bed_data:
                bed_info = {
                    'total_beds': facility.bed_count,
                    'available_beds': bed_data.available_beds,
                    'last_updated': bed_data.updated_at.isoformat() if bed_data.updated_at else None
                }
        except ImportError:
            pass
        
        response_data = {
            'valid': True,
            'facility_name': facility.name,
            'facility_type': facility.facility_type,
            'state': facility.state,
            'city': facility.city,
            'status': facility.status,
            'is_active': facility.status == 'active',
            'bed_info': bed_info,
            'contact_info': {
                'phone': facility.phone_number,
                'email': facility.email,
            } if hasattr(facility, 'phone_number') else None
        }
        
        return JsonResponse(response_data)
        
    except Facility.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Facility not found'}, status=404)
    except Exception as e:
        logger.error(f"Error validating facility {inspection_number}: {str(e)}")
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

# Add these new views to your existing user_management/views.py file

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
    
    # Get recent bed updates
    bed_data = None
    recent_bed_updates = []
    try:
        from bedupdates.models import BedAvailability
        bed_data = BedAvailability.objects.filter(facility=facility).first()
        if bed_data:
            # You might want to create a bed update history model for this
            recent_bed_updates = [bed_data]  # Placeholder for now
    except ImportError:
        pass
    
    context = {
        'facility': facility,
        'user_profile': user_profile,
        'change_logs': change_logs,
        'submission': submission,
        'bed_data': bed_data,
        'recent_bed_updates': recent_bed_updates,
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
    
    # Import the form from facility_admin (reuse the same form)
    try:
        from facility_admin.forms import FacilityForm
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
                    'address': facility.address,
                    'contact': facility.contact,
                    'contact_person': facility.contact_person,
                    'bed_count': facility.bed_count,
                }
                
                form = FacilityForm(request.POST, request.FILES, instance=facility)
                
                if form.is_valid():
                    # For staff updates, we might want to require admin approval
                    # depending on your business logic
                    updated_facility = form.save(commit=False)
                    
                    # Prevent staff from changing inspection number and bed count
                    updated_facility.inspection_number = facility.inspection_number
                    updated_facility.bed_count = facility.bed_count
                    
                    # Option 1: Direct update (if you trust facility staff)
                    updated_facility.save()
                    
                    # Option 2: Mark for admin review (commented out)
                    # updated_facility.status = 'pending_update'
                    # updated_facility.save()
                    
                    # Log the changes
                    try:
                        from search.models import FacilityChangeLog
                        new_values = {
                            'name': updated_facility.name,
                            'facility_type': updated_facility.facility_type,
                            'address': updated_facility.address,
                            'contact': updated_facility.contact,
                            'contact_person': updated_facility.contact_person,
                            'bed_count': updated_facility.bed_count,
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
                    
        except Exception as e:
            logger.error(f"Error updating facility for user {request.user.username}: {str(e)}")
            messages.error(request, "An error occurred while updating facility information. Please try again.")
    else:
        form = FacilityForm(instance=facility)
        
        # Make inspection number and bed count readonly for staff
        form.fields['inspection_number'].widget.attrs['readonly'] = True
        form.fields['inspection_number'].widget.attrs['class'] = form.fields['inspection_number'].widget.attrs.get('class', '') + ' readonly-field'
        form.fields['bed_count'].widget.attrs['readonly'] = True
        form.fields['bed_count'].widget.attrs['class'] = form.fields['bed_count'].widget.attrs.get('class', '') + ' readonly-field'
    
    context = {
        'form': form,
        'facility': facility,
        'user_profile': user_profile,
        'title': f'Update {facility.name}',
        'submit_text': 'Update Facility Information',
        'is_staff_update': True,
    }
    
    return render(request, 'user_management/facility_update_staff.html', context)



# Add these new views to your existing user_management/views.py file

@login_required
def facility_bed_update_staff(request):
    """Facility staff bed management - same functionality as admin portal but facility-specific"""
    
    print(f"\n🛏️ FACILITY BED MANAGEMENT ACCESS: {request.user.username}")
    print(f"🕒 Access Time: {timezone.now()}")
    
    # Enhanced user type checking
    try:
        user_profile = request.user.user_profile
        if user_profile.user_type != 'facility_staff':
            messages.error(request, "Access denied - facility staff access required.")
            logger.warning(f"Non-facility user {request.user.username} attempted to access bed management")
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
        messages.error(request, f"Bed management not available. Facility status: {facility.get_status_display()}. Please contact administrator.")
        return redirect('user_management:facility_dashboard')
    
    # Import bed models
    try:
        from bedupdates.models import BedAvailability
        from bedupdates.forms import BedAvailabilityForm
    except ImportError:
        messages.error(request, "Bed management system not available. Please contact administrator.")
        return redirect('user_management:facility_dashboard')
    
    # Get or create bed data for this facility
    bed_data, created = BedAvailability.objects.get_or_create(facility=facility)
    facility_bed_count = facility.bed_count  # Get the official bed count from Facility model
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                form = BedAvailabilityForm(request.POST, instance=bed_data)
                if form.is_valid():
                    bed_update = form.save(commit=False)
                    # Set the updated_at timestamp to current localized time
                    bed_update.updated_at = timezone.localtime(timezone.now())
                    bed_update.save()
                    
                    # Log the bed update
                    logger.info(f"Bed availability updated by facility staff {request.user.username} for facility {facility.name}")
                    
                    messages.success(request, f"Bed information for {facility.name} has been updated successfully.")
                    return redirect('user_management:facility_bed_update_staff')
                else:
                    messages.error(request, "Please correct the errors in the bed update form.")
                    
        except Exception as e:
            logger.error(f"Error updating bed information for user {request.user.username}: {str(e)}")
            messages.error(request, "An error occurred while updating bed information. Please try again.")
    else:
        form = BedAvailabilityForm(instance=bed_data)
        form.fields['facility'].initial = facility
    
    context = {
        'facility': facility,
        'form': form,
        'bed_data': bed_data,
        'facility_bed_count': facility_bed_count,
        'user_profile': user_profile,
        'is_staff_view': True,  # Flag to indicate this is staff view
    }
    
    return render(request, 'user_management/facility_bed_update_staff.html', context)
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
    
    # Get recent bed updates
    bed_data = None
    recent_bed_updates = []
    try:
        from bedupdates.models import BedAvailability
        bed_data = BedAvailability.objects.filter(facility=facility).first()
        if bed_data:
            # You might want to create a bed update history model for this
            recent_bed_updates = [bed_data]  # Placeholder for now
    except ImportError:
        pass
    
    context = {
        'facility': facility,
        'user_profile': user_profile,
        'change_logs': change_logs,
        'submission': submission,
        'bed_data': bed_data,
        'recent_bed_updates': recent_bed_updates,
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
                    
                    # The inspection_number and bed_count remain unchanged automatically
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
    
    # No need to modify readonly fields since they're not in this form
    
    context = {
        'form': form,
        'facility': facility,
        'user_profile': user_profile,
        'title': f'Update {facility.name}',
        'submit_text': 'Update Facility Information',
        'is_staff_update': True,
    }
    
    return render(request, 'user_management/facility_update_staff.html', context)
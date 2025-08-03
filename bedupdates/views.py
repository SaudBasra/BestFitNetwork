# bedupdates/views.py - Updated views for room-based bed management

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError
import json
import logging

from search.models import Facility
from .models import FacilityConfiguration, Room, Bed, BedAvailability
from .forms import RoomConfigurationForm, BedUpdateForm

logger = logging.getLogger(__name__)

def get_user_facility(request):
    """Helper function to get facility for current user"""
    try:
        if hasattr(request.user, 'user_profile') and request.user.user_profile.facility:
            return request.user.user_profile.facility
        return None
    except AttributeError:
        return None

@login_required
def facility_bed_management(request, facility_id=None):
    """Main bed management view - handles both configuration and matrix"""
    
    # Get facility
    if facility_id:
        facility = get_object_or_404(Facility, id=facility_id)
        # Check if user has access to this facility
        user_facility = get_user_facility(request)
        if user_facility and user_facility.id != facility.id:
            messages.error(request, "Access denied to this facility.")
            return redirect('bedupdates:bed_management')
    else:
        facility = get_user_facility(request)
        if not facility:
            facilities = Facility.objects.all().order_by('name')
            if request.GET.get('facility'):
                facility = get_object_or_404(Facility, id=request.GET.get('facility'))
            else:
                context = {'facilities': facilities}
                return render(request, 'bedupdates/facility_selection.html', context)
    
    # Get or create facility configuration
    config, created = FacilityConfiguration.objects.get_or_create(facility=facility)
    
    # Check if facility needs configuration
    if not config.is_configured:
        return redirect('bedupdates:configure_facility', facility_id=facility.id)
    
    # Get rooms and beds
    rooms = Room.objects.filter(facility_config=config, is_active=True).prefetch_related('beds')
    
    # Calculate statistics
    total_beds = sum(room.get_total_beds() for room in rooms)
    occupied_beds = sum(room.get_occupied_beds() for room in rooms)
    vacant_beds = total_beds - occupied_beds
    
    bed_stats = {
        'total_beds': total_beds,
        'occupied_beds': occupied_beds,
        'vacant_beds': vacant_beds,
        'occupancy_rate': (occupied_beds / total_beds * 100) if total_beds > 0 else 0
    }
    
    context = {
        'facility': facility,
        'config': config,
        'rooms': rooms,
        'bed_stats': bed_stats,
        'is_configured': config.is_configured,
    }
    
    return render(request, 'bedupdates/bed_management.html', context)

@login_required
def configure_facility(request, facility_id):
    """Facility configuration wizard"""
    facility = get_object_or_404(Facility, id=facility_id)
    
    # Check access
    user_facility = get_user_facility(request)
    if user_facility and user_facility.id != facility.id:
        messages.error(request, "Access denied to this facility.")
        return redirect('bedupdates:bed_management')
    
    config, created = FacilityConfiguration.objects.get_or_create(facility=facility)
    
    # Handle step-by-step configuration
    step = request.GET.get('step', '1')
    
    if step == '1':
        return configure_step_1(request, facility, config)
    elif step == '2':
        return configure_step_2(request, facility, config)
    elif step == '3':
        return configure_step_3(request, facility, config)
    else:
        return redirect('bedupdates:configure_facility', facility_id=facility.id)

def configure_step_1(request, facility, config):
    """Step 1: Get total number of rooms"""
    if request.method == 'POST':
        total_rooms = request.POST.get('total_rooms')
        try:
            total_rooms = int(total_rooms)
            if total_rooms <= 0:
                raise ValueError("Total rooms must be greater than 0")
            
            config.total_rooms = total_rooms
            config.save()
            
            return redirect(f'{reverse("bedupdates:configure_facility", args=[facility.id])}?step=2')
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid number of rooms.")
    
    context = {
        'facility': facility,
        'config': config,
        'step': 1,
        'total_steps': 3,
    }
    
    return render(request, 'bedupdates/configure_step_1.html', context)

def configure_step_2(request, facility, config):
    """Step 2: Configure each room"""
    if config.total_rooms <= 0:
        return redirect(f'{reverse("bedupdates:configure_facility", args=[facility.id])}?step=1')
    
    # Get current room being configured
    current_room = int(request.GET.get('room', 1))
    
    if request.method == 'POST':
        room_name = request.POST.get('room_name', '').strip()
        room_type = request.POST.get('room_type')
        num_beds = request.POST.get('num_beds')
        
        try:
            # Validation
            if not room_name:
                raise ValueError("Room name is required")
            
            if room_type not in ['private', 'shared']:
                raise ValueError("Invalid room type")
            
            num_beds = int(num_beds)
            if room_type == 'private' and num_beds != 1:
                raise ValueError("Private rooms must have exactly 1 bed")
            
            if room_type == 'shared' and num_beds < 2:
                raise ValueError("Shared rooms must have at least 2 beds")
            
            # Check if room name already exists
            existing_rooms = config.get_rooms()
            if any(room.get('name') == room_name for room in existing_rooms):
                raise ValueError("Room name already exists")
            
            # Store room configuration in session
            if 'rooms_config' not in request.session:
                request.session['rooms_config'] = []
            
            room_config = {
                'name': room_name,
                'type': room_type,
                'num_beds': num_beds,
                'room_number': current_room
            }
            
            # Update existing room or add new
            rooms_config = request.session['rooms_config']
            room_updated = False
            for i, room in enumerate(rooms_config):
                if room.get('room_number') == current_room:
                    rooms_config[i] = room_config
                    room_updated = True
                    break
            
            if not room_updated:
                rooms_config.append(room_config)
            
            request.session['rooms_config'] = rooms_config
            request.session.modified = True
            
            # Move to next room or final step
            if current_room < config.total_rooms:
                next_room = current_room + 1
                return redirect(f'{reverse("bedupdates:configure_facility", args=[facility.id])}?step=2&room={next_room}')
            else:
                return redirect(f'{reverse("bedupdates:configure_facility", args=[facility.id])}?step=3')
                
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    
    # Get current room config from session
    current_room_config = {}
    if 'rooms_config' in request.session:
        for room in request.session['rooms_config']:
            if room.get('room_number') == current_room:
                current_room_config = room
                break
    
    context = {
        'facility': facility,
        'config': config,
        'step': 2,
        'total_steps': 3,
        'current_room': current_room,
        'total_rooms': config.total_rooms,
        'current_room_config': current_room_config,
    }
    
    return render(request, 'bedupdates/configure_step_2.html', context)

def configure_step_3(request, facility, config):
    """Step 3: Review and confirm configuration"""
    rooms_config = request.session.get('rooms_config', [])
    
    if len(rooms_config) != config.total_rooms:
        messages.error(request, "Configuration incomplete. Please configure all rooms.")
        return redirect(f'{reverse("bedupdates:configure_facility", args=[facility.id])}?step=2')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Delete existing rooms if reconfiguring
                Room.objects.filter(facility_config=config).delete()
                
                # Create rooms and beds
                for room_config in rooms_config:
                    room = Room.objects.create(
                        facility_config=config,
                        room_name=room_config['name'],
                        room_type=room_config['type'],
                        room_number=str(room_config['room_number'])
                    )
                    
                    # Create beds for this room
                    for bed_num in range(1, room_config['num_beds'] + 1):
                        Bed.objects.create(
                            room=room,
                            bed_number=str(bed_num),
                            bed_id=f"{room_config['name']}-{bed_num}"
                        )
                
                # Update configuration
                config.configuration_data = {'rooms': rooms_config}
                config.is_configured = True
                config.save()
                
                # Clear session
                if 'rooms_config' in request.session:
                    del request.session['rooms_config']
                
                messages.success(request, f"Facility configuration completed successfully! {len(rooms_config)} rooms configured.")
                return redirect('bedupdates:bed_management', facility_id=facility.id)
                
        except Exception as e:
            logger.error(f"Error saving facility configuration: {str(e)}")
            messages.error(request, "Error saving configuration. Please try again.")
    
    # Calculate totals
    total_beds = sum(room['num_beds'] for room in rooms_config)
    private_rooms = [room for room in rooms_config if room['type'] == 'private']
    shared_rooms = [room for room in rooms_config if room['type'] == 'shared']
    
    context = {
        'facility': facility,
        'config': config,
        'step': 3,
        'total_steps': 3,
        'rooms_config': rooms_config,
        'total_beds': total_beds,
        'private_rooms': private_rooms,
        'shared_rooms': shared_rooms,
        'facility_bed_count': facility.bed_count,
    }
    
    return render(request, 'bedupdates/configure_step_3.html', context)

@login_required
def update_bed_status(request):
    """AJAX endpoint to update bed status"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bed_id = data.get('bed_id')
            new_status = data.get('status')
            new_gender = data.get('gender')
            
            bed = get_object_or_404(Bed, bed_id=bed_id)
            
            # Check access
            user_facility = get_user_facility(request)
            if user_facility and user_facility.id != bed.room.facility_config.facility.id:
                return JsonResponse({'success': False, 'error': 'Access denied'})
            
            # Validate status and gender
            if new_status not in ['vacant', 'occupied']:
                return JsonResponse({'success': False, 'error': 'Invalid status'})
            
            if new_gender not in ['neutral', 'male', 'female']:
                return JsonResponse({'success': False, 'error': 'Invalid gender'})
            
            # For shared rooms, enforce gender segregation
            if bed.room.room_type == 'shared' and new_status == 'occupied':
                if bed.room.room_gender == 'neutral':
                    # First occupancy sets room gender
                    bed.room.room_gender = new_gender
                    bed.room.save()
                    # Update all other beds to same gender, vacant status
                    bed.room.beds.exclude(id=bed.id).update(
                        gender=new_gender,
                        status='vacant'
                    )
                elif bed.room.room_gender != new_gender:
                    return JsonResponse({
                        'success': False, 
                        'error': f'This shared room is designated for {bed.room.room_gender} patients only'
                    })
            
            # Update bed
            old_status = bed.status
            bed.status = new_status
            bed.gender = new_gender
            
            if new_status == 'occupied':
                bed.admitted_date = timezone.now()
            else:
                bed.admitted_date = None
                bed.patient_name = ''
            
            bed.save()
            
            # If this was the last occupied bed in a shared room, reset room gender
            if (bed.room.room_type == 'shared' and new_status == 'vacant' and 
                not bed.room.beds.filter(status='occupied').exists()):
                bed.room.room_gender = 'neutral'
                bed.room.beds.update(gender='neutral')
                bed.room.save()
            
            return JsonResponse({
                'success': True,
                'bed_id': bed_id,
                'status': bed.status,
                'gender': bed.gender,
                'room_gender': bed.room.room_gender,
                'status_changed': old_status != new_status
            })
            
        except Exception as e:
            logger.error(f"Error updating bed status: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Server error'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def reconfigure_facility(request, facility_id):
    """Reset facility configuration and start over"""
    facility = get_object_or_404(Facility, id=facility_id)
    
    # Check access
    user_facility = get_user_facility(request)
    if user_facility and user_facility.id != facility.id:
        messages.error(request, "Access denied to this facility.")
        return redirect('bedupdates:bed_management')
    
    if request.method == 'POST':
        config = get_object_or_404(FacilityConfiguration, facility=facility)
        
        # Reset configuration
        config.is_configured = False
        config.total_rooms = 0
        config.configuration_data = {}
        config.save()
        
        # Delete all rooms and beds
        Room.objects.filter(facility_config=config).delete()
        
        # Clear session
        if 'rooms_config' in request.session:
            del request.session['rooms_config']
        
        messages.success(request, "Facility configuration has been reset. Please configure your facility again.")
        return redirect('bedupdates:configure_facility', facility_id=facility.id)
    
    context = {
        'facility': facility,
    }
    
    return render(request, 'bedupdates/reconfigure_confirm.html', context)

# Legacy views for backward compatibility
def bed_update_view(request):
    """Legacy view - redirect to new bed management"""
    facility_id = request.GET.get('facility')
    if facility_id:
        return redirect('bedupdates:bed_management', facility_id=facility_id)
    return redirect('bedupdates:bed_management')

def facility_dashboard_view(request):
    """Dashboard showing all facilities bed statistics"""
    facilities = Facility.objects.all()
    facility_stats = []
    
    for facility in facilities:
        try:
            config = facility.facility_configuration
            if config.is_configured:
                rooms = Room.objects.filter(facility_config=config, is_active=True)
                total_beds = sum(room.get_total_beds() for room in rooms)
                occupied_beds = sum(room.get_occupied_beds() for room in rooms)
                
                facility_stats.append({
                    'facility': facility,
                    'total_beds': total_beds,
                    'occupied_beds': occupied_beds,
                    'vacant_beds': total_beds - occupied_beds,
                    'occupancy_rate': (occupied_beds / total_beds * 100) if total_beds > 0 else 0,
                    'is_configured': True
                })
            else:
                facility_stats.append({
                    'facility': facility,
                    'is_configured': False
                })
        except FacilityConfiguration.DoesNotExist:
            facility_stats.append({
                'facility': facility,
                'is_configured': False
            })
    
    context = {
        'facility_stats': facility_stats,
        'total_facilities': len(facility_stats),
        'configured_facilities': len([f for f in facility_stats if f.get('is_configured', False)]),
    }
    
    return render(request, 'bedupdates/dashboard.html', context)
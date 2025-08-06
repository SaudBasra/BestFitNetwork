# bedupdates/views.py - Updated with improved bed management

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

def sync_with_legacy_bed_availability(facility):
    """Sync advanced bed system with legacy BedAvailability model for search engine compatibility"""
    try:
        config = FacilityConfiguration.objects.get(facility=facility)
        if not config.is_configured:
            return
        
        # Get rooms and calculate bed counts
        rooms = Room.objects.filter(facility_config=config, is_active=True)
        
        # Calculate bed counts by type and status
        private_beds_total = 0
        private_beds_available = 0
        shared_beds_male_total = 0
        shared_beds_male_available = 0
        shared_beds_female_total = 0
        shared_beds_female_available = 0
        
        for room in rooms:
            beds = room.beds.all()
            
            if room.room_type == 'private':
                private_beds_total += beds.count()
                private_beds_available += beds.filter(status='vacant').count()
            elif room.room_type == 'shared':
                # For shared rooms, count by gender
                male_beds = beds.filter(gender='male')
                female_beds = beds.filter(gender='female')
                
                shared_beds_male_total += male_beds.count()
                shared_beds_male_available += male_beds.filter(status='vacant').count()
                
                shared_beds_female_total += female_beds.count()
                shared_beds_female_available += female_beds.filter(status='vacant').count()
        
        # Calculate total available beds
        total_available = private_beds_available + shared_beds_male_available + shared_beds_female_available
        
        # Update or create legacy BedAvailability record
        bed_availability, created = BedAvailability.objects.get_or_create(
            facility=facility,
            defaults={
                'available_beds': total_available,
                'shared_beds_total': shared_beds_male_total + shared_beds_female_total,
                'shared_beds_male': shared_beds_male_available,
                'shared_beds_female': shared_beds_female_available,
                'separate_beds_total': private_beds_total,
                'separate_beds_male': private_beds_available,
                'separate_beds_female': private_beds_available,
            }
        )
        
        if not created:
            # Update existing record
            bed_availability.available_beds = total_available
            bed_availability.shared_beds_total = shared_beds_male_total + shared_beds_female_total
            bed_availability.shared_beds_male = shared_beds_male_available
            bed_availability.shared_beds_female = shared_beds_female_available
            bed_availability.separate_beds_total = private_beds_total
            bed_availability.separate_beds_male = private_beds_available
            bed_availability.separate_beds_female = private_beds_available
            bed_availability.updated_at = timezone.now()
            bed_availability.save()
        
        logger.info(f"Synced bed availability for {facility.name}: {total_available} total available beds")
        
    except FacilityConfiguration.DoesNotExist:
        logger.warning(f"No bed configuration found for facility {facility.name}")
    except Exception as e:
        logger.error(f"Error syncing bed availability for {facility.name}: {str(e)}")

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
    rooms = Room.objects.filter(facility_config=config, is_active=True).prefetch_related('beds').order_by('room_number')
    
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
    
    # Sync with legacy system
    sync_with_legacy_bed_availability(facility)
    
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
                        # For shared rooms, start with neutral gender
                        # For private rooms, also start neutral
                        gender = 'neutral'
                        
                        Bed.objects.create(
                            room=room,
                            bed_number=str(bed_num),
                            bed_id=f"{room_config['name']}-{bed_num}",
                            gender=gender,
                            status='vacant'
                        )
                
                # Update configuration
                config.configuration_data = {'rooms': rooms_config}
                config.is_configured = True
                config.save()
                
                # Sync with legacy system immediately after configuration
                sync_with_legacy_bed_availability(facility)
                
                # Clear session
                if 'rooms_config' in request.session:
                    del request.session['rooms_config']
                
                logger.info(f"Facility {facility.name} configured successfully with {len(rooms_config)} rooms")
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
            patient_name = data.get('patient_name', '')
            notes = data.get('notes', '')
            
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
                # Check if there are already occupied beds with a different gender
                occupied_beds = bed.room.beds.filter(status='occupied').exclude(id=bed.id)
                if occupied_beds.exists():
                    existing_gender = occupied_beds.first().gender
                    if existing_gender != 'neutral' and existing_gender != new_gender:
                        return JsonResponse({
                            'success': False, 
                            'error': f'This shared room is designated for {existing_gender} patients only'
                        })
                
                # Set all vacant beds in shared room to same gender when first bed is occupied
                if not occupied_beds.exists():
                    bed.room.beds.filter(status='vacant').update(gender=new_gender)
            
            # Update bed
            old_status = bed.status
            bed.status = new_status
            bed.gender = new_gender
            bed.patient_name = patient_name
            bed.notes = notes
            
            if new_status == 'occupied':
                bed.admitted_date = timezone.now()
            else:
                bed.admitted_date = None
                bed.patient_name = ''
                
                # If this was the last occupied bed in a shared room, reset all beds to neutral
                if (bed.room.room_type == 'shared' and 
                    not bed.room.beds.filter(status='occupied').exists()):
                    bed.room.beds.update(gender='neutral')
            
            bed.save()
            
            # Sync with legacy system after bed update
            sync_with_legacy_bed_availability(bed.room.facility_config.facility)
            
            logger.info(f"Bed {bed_id} updated: {old_status} -> {new_status}, {bed.gender}")
            
            # Format updated time for response
            updated_time = timezone.now()
            bed.updated_at = updated_time
            bed.save()
            
            return JsonResponse({
                'success': True,
                'bed_id': bed_id,
                'status': bed.status,
                'gender': bed.gender,
                'status_changed': old_status != new_status,
                'updated_at': updated_time.strftime('%b %d, %Y at %I:%M %p')
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
        
        try:
            with transaction.atomic():
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
                
                # Reset legacy bed availability to default
                BedAvailability.objects.filter(facility=facility).update(
                    available_beds=facility.bed_count or 0,
                    shared_beds_total=0,
                    shared_beds_male=0,
                    shared_beds_female=0,
                    separate_beds_total=0,
                    separate_beds_male=0,
                    separate_beds_female=0,
                    updated_at=timezone.now()
                )
                
                logger.info(f"Facility {facility.name} configuration reset by user {request.user.username}")
                messages.success(request, "Facility configuration has been reset. Please configure your facility again.")
                return redirect('bedupdates:configure_facility', facility_id=facility.id)
                
        except Exception as e:
            logger.error(f"Error resetting facility configuration: {str(e)}")
            messages.error(request, "Error resetting configuration. Please try again.")
    
    context = {
        'facility': facility,
    }
    
    return render(request, 'bedupdates/reconfigure_confirm.html', context)

# Legacy views for backward compatibility
def bed_update_view(request):
    """Legacy view - redirect to new bed management or show legacy form"""
    facility_id = request.GET.get('facility')
    
    if facility_id:
        facility = get_object_or_404(Facility, id=facility_id)
        
        # Check if facility has advanced configuration
        try:
            config = FacilityConfiguration.objects.get(facility=facility)
            if config.is_configured:
                # Redirect to advanced system
                messages.info(request, "This facility uses the advanced bed management system.")
                return redirect('bedupdates:bed_management', facility_id=facility.id)
        except FacilityConfiguration.DoesNotExist:
            pass
        
        # Show legacy form
        bed_data, created = BedAvailability.objects.get_or_create(facility=facility)
        
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    available_beds = int(request.POST.get('available_beds', 0))
                    
                    # Validate against facility bed count
                    if facility.bed_count and available_beds > facility.bed_count:
                        messages.error(request, f"Available beds ({available_beds}) cannot exceed total bed count ({facility.bed_count})")
                    else:
                        bed_data.available_beds = available_beds
                        bed_data.updated_at = timezone.now()
                        bed_data.save()
                        
                        logger.info(f"Legacy bed update for {facility.name}: {available_beds} available beds")
                        messages.success(request, "Bed availability updated successfully!")
                        return redirect(f'{reverse("bedupdates:bed_update_view")}?facility={facility.id}')
                        
            except (ValueError, TypeError):
                messages.error(request, "Please enter a valid number for available beds.")
            except Exception as e:
                logger.error(f"Error updating legacy bed data: {str(e)}")
                messages.error(request, "Error updating bed information. Please try again.")
        
        context = {
            'facility': facility,
            'bed_data': bed_data,
            'is_legacy': True,
        }
        
        return render(request, 'bedupdates/legacy_bed_update.html', context)
    
    # No facility specified, show facility selection
    facilities = Facility.objects.all().order_by('name')
    context = {'facilities': facilities}
    return render(request, 'bedupdates/facility_selection.html', context)

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
                    'is_configured': True,
                    'system_type': 'advanced'
                })
            else:
                facility_stats.append({
                    'facility': facility,
                    'is_configured': False,
                    'system_type': 'not_configured'
                })
        except FacilityConfiguration.DoesNotExist:
            # Check for legacy data
            try:
                bed_data = BedAvailability.objects.get(facility=facility)
                total_beds = facility.bed_count or 0
                available_beds = bed_data.available_beds
                occupied_beds = max(0, total_beds - available_beds)
                
                facility_stats.append({
                    'facility': facility,
                    'total_beds': total_beds,
                    'occupied_beds': occupied_beds,
                    'vacant_beds': available_beds,
                    'occupancy_rate': (occupied_beds / total_beds * 100) if total_beds > 0 else 0,
                    'is_configured': True,
                    'system_type': 'legacy'
                })
            except BedAvailability.DoesNotExist:
                facility_stats.append({
                    'facility': facility,
                    'is_configured': False,
                    'system_type': 'no_data'
                })
    
    context = {
        'facility_stats': facility_stats,
        'total_facilities': len(facility_stats),
        'configured_facilities': len([f for f in facility_stats if f.get('is_configured', False)]),
        'advanced_facilities': len([f for f in facility_stats if f.get('system_type') == 'advanced']),
        'legacy_facilities': len([f for f in facility_stats if f.get('system_type') == 'legacy']),
    }
    
    return render(request, 'bedupdates/dashboard.html', context)
# facility_admin/views.py - Updated with bed management integration
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, F, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.decorators.http import require_POST
import csv
import io

# Import all the models from search app
from search.models import Facility, FacilitySubmission, FacilityChangeLog
from bedupdates.models import BedAvailability  # Import bed availability model
from .forms import (
    FacilityForm, PublicRegistrationForm, BulkImportForm, 
    ApprovalForm, FacilityFilterForm
)

# ✅ Auth function - this checks if user is admin
def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard with quick stats, recent activity, and bed statistics"""
    
    # Quick stats for facilities
    stats = {
        'total_facilities': Facility.objects.count(),
        'active_facilities': Facility.objects.filter(status='active').count(),
        'pending_facilities': Facility.objects.filter(status='pending').count(),
        'inactive_facilities': Facility.objects.filter(status='inactive').count(),
    }
    
    # Bed statistics
    bed_stats = BedAvailability.objects.aggregate(
        total_beds=Coalesce(Sum(F('shared_beds_total') + F('separate_beds_total')), Value(0), output_field=IntegerField()),
        available_beds=Coalesce(Sum('available_beds'), Value(0), output_field=IntegerField()),
        total_shared=Coalesce(Sum('shared_beds_total'), Value(0), output_field=IntegerField()),
        total_separate=Coalesce(Sum('separate_beds_total'), Value(0), output_field=IntegerField()),
    )
    
    # Calculate official bed count from facilities
    total_official_beds = Facility.objects.aggregate(Sum('bed_count'))['bed_count__sum'] or 0
    
    # Get facilities with low bed availability (less than 10% available)
    low_availability = []
    for facility in Facility.objects.filter(status='active'):
        try:
            bed = facility.bed_availability
            total_beds = bed.shared_beds_total + bed.separate_beds_total
            if total_beds > 0 and (bed.available_beds / total_beds) < 0.1:
                low_availability.append({
                    'facility': facility,
                    'available': bed.available_beds,
                    'total': total_beds,
                    'percentage': (bed.available_beds / total_beds) * 100
                })
        except BedAvailability.DoesNotExist:
            pass
    
    # User tracking stats (if usertracking app is available)
    user_stats = {'total_inquiries': 0, 'conversions': 0}
    try:
        from usertracking.models import UserTracking
        user_stats = {
            'total_inquiries': UserTracking.objects.count(),
            'conversions': UserTracking.objects.filter(joined_facility=True).count(),
        }
    except (ImportError, AttributeError):
        # usertracking app not available or not installed
        pass
    
    # Recent activity
    recent_submissions = Facility.objects.filter(status='pending').order_by('-created_at')[:5]
    recent_changes = FacilityChangeLog.objects.select_related('facility', 'changed_by').order_by('-timestamp')[:10]
    
    context = {
        'stats': stats,
        'bed_stats': bed_stats,
        'total_official_beds': total_official_beds,
        'low_availability': low_availability,
        'user_stats': user_stats,
        'recent_submissions': recent_submissions,
        'recent_changes': recent_changes,
    }
    
    return render(request, 'facility_admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def facility_list(request):
    """List all facilities with filtering and search"""
    
    form = FacilityFilterForm(request.GET)
    facilities = Facility.objects.all().order_by('-created_at')
    
    # Apply filters
    if form.is_valid():
        if form.cleaned_data['status']:
            facilities = facilities.filter(status=form.cleaned_data['status'])
        if form.cleaned_data['facility_type']:
            facilities = facilities.filter(facility_type=form.cleaned_data['facility_type'])
        if form.cleaned_data['state']:
            facilities = facilities.filter(state__icontains=form.cleaned_data['state'])
        if form.cleaned_data['search']:
            search_term = form.cleaned_data['search']
            facilities = facilities.filter(
                Q(name__icontains=search_term) |
                Q(address__icontains=search_term) |
                Q(contact_person__icontains=search_term)
            )
    
    # Pagination
    paginator = Paginator(facilities, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'facilities': page_obj,
    }
    
    return render(request, 'facility_admin/facility_list.html', context)


@login_required
@user_passes_test(is_admin)
def facility_create(request):
    """Create new facility (Admin direct entry)"""
    
    if request.method == 'POST':
        form = FacilityForm(request.POST, request.FILES)
        if form.is_valid():
            facility = form.save(commit=False)
            facility.submitted_by = request.user
            facility.submission_type = 'admin'
            facility.status = 'active'  # Admin entries are immediately active
            facility.approved_by = request.user
            facility.approved_at = timezone.now()
            facility.save()
            
            # Create initial bed availability record
            BedAvailability.objects.get_or_create(
                facility=facility,
                defaults={
                    'available_beds': 0,
                    'shared_beds_total': 0,
                    'shared_beds_male': 0,
                    'shared_beds_female': 0,
                    'separate_beds_total': 0,
                    'separate_beds_male': 0,
                    'separate_beds_female': 0,
                }
            )
            
            # Log the creation
            FacilityChangeLog.objects.create(
                facility=facility,
                changed_by=request.user,
                change_type='created',
                new_values={'status': 'active', 'created_by_admin': True}
            )
            
            messages.success(request, f'Facility "{facility.name}" created successfully!')
            return redirect('facility_admin:facility_list')
    else:
        form = FacilityForm()
    
    return render(request, 'facility_admin/facility_form.html', {
        'form': form,
        'title': 'Add New Facility',
        'submit_text': 'Create Facility'
    })


@login_required
@user_passes_test(is_admin)
def facility_edit(request, facility_id):
    """Edit existing facility"""
    
    facility = get_object_or_404(Facility, id=facility_id)
    old_values = {
        'name': facility.name,
        'status': facility.status,
        'facility_type': facility.facility_type,
        'bed_count': facility.bed_count,
    }
    
    if request.method == 'POST':
        form = FacilityForm(request.POST, request.FILES, instance=facility)
        if form.is_valid():
            updated_facility = form.save()
            
            # Create bed availability record if it doesn't exist
            BedAvailability.objects.get_or_create(
                facility=updated_facility,
                defaults={
                    'available_beds': 0,
                    'shared_beds_total': 0,
                    'shared_beds_male': 0,
                    'shared_beds_female': 0,
                    'separate_beds_total': 0,
                    'separate_beds_male': 0,
                    'separate_beds_female': 0,
                }
            )
            
            # Log the changes
            new_values = {
                'name': updated_facility.name,
                'status': updated_facility.status,
                'facility_type': updated_facility.facility_type,
                'bed_count': updated_facility.bed_count,
            }
            
            FacilityChangeLog.objects.create(
                facility=updated_facility,
                changed_by=request.user,
                change_type='updated',
                old_values=old_values,
                new_values=new_values
            )
            
            messages.success(request, f'Facility "{facility.name}" updated successfully!')
            return redirect('facility_admin:facility_list')
    else:
        form = FacilityForm(instance=facility)
    
    return render(request, 'facility_admin/facility_form.html', {
        'form': form,
        'facility': facility,
        'title': f'Edit {facility.name}',
        'submit_text': 'Update Facility'
    })


def public_registration(request):
    """Public facility registration form - NO login required"""
    
    if request.method == 'POST':
        facility_form = PublicRegistrationForm(request.POST, request.FILES)
        
        if facility_form.is_valid():
            # Create facility with pending status
            facility = facility_form.save(commit=False)
            facility.submission_type = 'self_register'
            facility.status = 'pending'
            facility.save()
            
            # Create initial bed availability record
            BedAvailability.objects.get_or_create(
                facility=facility,
                defaults={
                    'available_beds': 0,
                    'shared_beds_total': 0,
                    'shared_beds_male': 0,
                    'shared_beds_female': 0,
                    'separate_beds_total': 0,
                    'separate_beds_male': 0,
                    'separate_beds_female': 0,
                }
            )
            
            # Create submission record
            submission = FacilitySubmission.objects.create(
                facility=facility,
                submitter_name=facility_form.cleaned_data['submitter_name'],
                submitter_email=facility_form.cleaned_data['submitter_email'],
                submitter_phone=facility_form.cleaned_data['submitter_phone'],
                submission_notes=facility_form.cleaned_data.get('submission_notes', '')
            )
            
            # Log the submission
            FacilityChangeLog.objects.create(
                facility=facility,
                changed_by=None,  # No user for public submissions
                change_type='created',
                new_values={
                    'status': 'pending',
                    'submission_type': 'self_register',
                    'submitter': facility_form.cleaned_data['submitter_name']
                }
            )
            
            messages.success(
                request, 
                'Thank you! Your facility has been submitted for review. '
                'You will be contacted once it\'s approved.'
            )
            return redirect('facility_admin:public_registration')
    else:
        facility_form = PublicRegistrationForm()
    
    return render(request, 'facility_admin/public_registration.html', {
        'form': facility_form
    })


@login_required
@user_passes_test(is_admin)
def approval_queue(request):
    """View pending facilities awaiting approval"""
    
    pending_facilities = Facility.objects.filter(status='pending').select_related('facilitysubmission').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(pending_facilities, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'facility_admin/approval_queue.html', {
        'page_obj': page_obj,
        'pending_facilities': page_obj
    })


@login_required
@user_passes_test(is_admin)
def facility_approve(request, facility_id):
    """Approve or reject a facility - works for any status"""
    
    facility = get_object_or_404(Facility, id=facility_id)
    
    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            admin_notes = form.cleaned_data['admin_notes']
            rejection_reason = form.cleaned_data.get('rejection_reason', '')
            
            old_status = facility.status
            
            if action == 'approve':
                facility.status = 'active'
                facility.approved_by = request.user
                facility.approved_at = timezone.now()
                facility.save()
                
                # Create bed availability record if it doesn't exist
                BedAvailability.objects.get_or_create(
                    facility=facility,
                    defaults={
                        'available_beds': 0,
                        'shared_beds_total': 0,
                        'shared_beds_male': 0,
                        'shared_beds_female': 0,
                        'separate_beds_total': 0,
                        'separate_beds_male': 0,
                        'separate_beds_female': 0,
                    }
                )
                
                # Update submission record if it exists
                try:
                    submission = facility.facilitysubmission
                    submission.admin_notes = admin_notes
                    submission.reviewed_at = timezone.now()
                    submission.save()
                except FacilitySubmission.DoesNotExist:
                    pass
                
                # Log approval
                FacilityChangeLog.objects.create(
                    facility=facility,
                    changed_by=request.user,
                    change_type='approved',
                    old_values={'status': old_status},
                    new_values={'status': 'active'},
                    notes=admin_notes
                )
                
                messages.success(request, f'Facility "{facility.name}" has been approved!')
                
            elif action == 'reject':
                facility.status = 'rejected'
                facility.save()
                
                # Update submission record if it exists
                try:
                    submission = facility.facilitysubmission
                    submission.admin_notes = admin_notes
                    submission.rejection_reason = rejection_reason
                    submission.reviewed_at = timezone.now()
                    submission.save()
                except FacilitySubmission.DoesNotExist:
                    pass
                
                # Log rejection
                FacilityChangeLog.objects.create(
                    facility=facility,
                    changed_by=request.user,
                    change_type='rejected',
                    old_values={'status': old_status},
                    new_values={'status': 'rejected'},
                    notes=f"Rejection reason: {rejection_reason}"
                )
                
                messages.warning(request, f'Facility "{facility.name}" has been rejected.')
            
            # Redirect based on where they came from
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            elif old_status == 'pending':
                return redirect('facility_admin:approval_queue')
            else:
                return redirect('facility_admin:facility_list')
    else:
        form = ApprovalForm()
    
    return render(request, 'facility_admin/facility_approve.html', {
        'facility': facility,
        'form': form
    })


@login_required
@user_passes_test(is_admin)
def bulk_import(request):
    """Bulk import facilities from CSV with enhanced error handling"""
    
    if request.method == 'POST':
        form = BulkImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            try:
                # Read CSV file with better encoding handling
                file_content = csv_file.read()
                
                # Try different encodings
                for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                    try:
                        decoded_content = file_content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise ValueError("Could not decode CSV file. Please ensure it's saved in UTF-8 format.")
                
                # Enhanced CSV parsing with multiple delimiter detection
                import csv
                import io
                
                # Detect delimiter
                sample = decoded_content[:1024]
                sniffer = csv.Sniffer()
                try:
                    delimiter = sniffer.sniff(sample, delimiters=',;\t|').delimiter
                except:
                    delimiter = ','  # Default to comma
                
                # Parse CSV with detected delimiter
                csv_reader = csv.DictReader(io.StringIO(decoded_content), delimiter=delimiter)
                
                # Get the fieldnames (headers)
                fieldnames = csv_reader.fieldnames
                
                if not fieldnames:
                    raise ValueError("CSV file appears to be empty or has no headers.")
                
                # Clean fieldnames (remove quotes, extra spaces)
                cleaned_fieldnames = [field.strip().strip('"\'') for field in fieldnames]
                
                # Map CSV fields to our model fields (case-insensitive)
                field_mapping = {}
                required_fields = ['name', 'type', 'inspection number', 'address', 'state', 'county', 'bed count']
                
                # Create case-insensitive mapping
                for field in cleaned_fieldnames:
                    field_lower = field.lower().strip()
                    if 'name' in field_lower and 'contact' not in field_lower:
                        field_mapping['name'] = field
                    elif 'type' in field_lower:
                        field_mapping['type'] = field
                    elif 'inspection' in field_lower:
                        field_mapping['inspection_number'] = field
                    elif 'address' in field_lower:
                        field_mapping['address'] = field
                    elif 'state' in field_lower:
                        field_mapping['state'] = field
                    elif 'county' in field_lower:
                        field_mapping['county'] = field
                    elif 'bed' in field_lower:
                        field_mapping['bed_count'] = field
                    elif 'endorsement' in field_lower:
                        field_mapping['endorsement'] = field
                    elif 'contact person' in field_lower:
                        field_mapping['contact_person'] = field
                    elif 'contact' in field_lower:
                        field_mapping['contact'] = field
                
                # Check for missing required fields
                missing_required = []
                for req_field in required_fields:
                    mapped_field = req_field.replace(' ', '_')
                    if mapped_field not in field_mapping:
                        missing_required.append(req_field.title())
                
                if missing_required:
                    messages.error(request, 
                        f"Missing required columns: {', '.join(missing_required)}. "
                        f"Found columns: {', '.join(cleaned_fieldnames)}. "
                        "Please download the template for the correct format.")
                    return redirect('facility_admin:bulk_import')
                
                # Process the CSV data
                imported_count = 0
                errors = []
                warnings = []
                
                # Reset the reader
                csv_reader = csv.DictReader(io.StringIO(decoded_content), delimiter=delimiter)
                
                for row_num, row in enumerate(csv_reader, start=2):
                    try:
                        # Clean row data
                        cleaned_row = {}
                        for key, value in row.items():
                            if key:  # Skip None keys
                                cleaned_key = key.strip().strip('"\'')
                                cleaned_value = str(value).strip().strip('"\'') if value else ''
                                cleaned_row[cleaned_key] = cleaned_value
                        
                        # Extract data using our field mapping
                        facility_data = {}
                        
                        # Required fields
                        try:
                            facility_data['name'] = cleaned_row[field_mapping['name']]
                            facility_data['facility_type'] = cleaned_row[field_mapping['type']]
                            facility_data['inspection_number'] = cleaned_row[field_mapping['inspection_number']]
                            facility_data['address'] = cleaned_row[field_mapping['address']]
                            facility_data['state'] = cleaned_row[field_mapping['state']]
                            facility_data['county'] = cleaned_row[field_mapping['county']]
                            
                            # Handle bed count conversion
                            bed_count_str = cleaned_row[field_mapping['bed_count']]
                            facility_data['bed_count'] = int(bed_count_str) if bed_count_str and bed_count_str.isdigit() else 0
                            
                        except (KeyError, ValueError) as e:
                            errors.append(f"Row {row_num}: Missing or invalid required field - {str(e)}")
                            continue
                        
                        # Optional fields
                        facility_data['endorsement'] = cleaned_row.get(field_mapping.get('endorsement', ''), '')
                        facility_data['contact'] = cleaned_row.get(field_mapping.get('contact', ''), '')
                        facility_data['contact_person'] = cleaned_row.get(field_mapping.get('contact_person', ''), '')
                        
                        # Validate required fields are not empty
                        if not all([facility_data['name'], facility_data['facility_type'], 
                                   facility_data['inspection_number'], facility_data['address'],
                                   facility_data['state'], facility_data['county']]):
                            errors.append(f"Row {row_num}: One or more required fields are empty")
                            continue
                        
                        # Check for duplicate inspection number
                        if Facility.objects.filter(inspection_number=facility_data['inspection_number']).exists():
                            warnings.append(f"Row {row_num}: Inspection number {facility_data['inspection_number']} already exists - skipped")
                            continue
                        
                        # Create facility
                        facility = Facility(
                            name=facility_data['name'],
                            facility_type=facility_data['facility_type'],
                            endorsement=facility_data['endorsement'],
                            inspection_number=facility_data['inspection_number'],
                            address=facility_data['address'],
                            state=facility_data['state'],
                            county=facility_data['county'],
                            contact=facility_data['contact'],
                            contact_person=facility_data['contact_person'],
                            bed_count=facility_data['bed_count'],
                            submitted_by=request.user,
                            submission_type='bulk_import',
                            status='active',  # Bulk imports are immediately active
                            approved_by=request.user,
                            approved_at=timezone.now()
                        )
                        facility.save()
                        
                        # Create initial bed availability record
                        BedAvailability.objects.get_or_create(
                            facility=facility,
                            defaults={
                                'available_beds': 0,
                                'shared_beds_total': 0,
                                'shared_beds_male': 0,
                                'shared_beds_female': 0,
                                'separate_beds_total': 0,
                                'separate_beds_male': 0,
                                'separate_beds_female': 0,
                            }
                        )
                        
                        # Log the import
                        FacilityChangeLog.objects.create(
                            facility=facility,
                            changed_by=request.user,
                            change_type='created',
                            new_values={'imported_from_csv': True, 'row_number': row_num}
                        )
                        
                        imported_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                
                # Show results
                if imported_count > 0:
                    messages.success(request, f'Successfully imported {imported_count} facilities!')
                
                if warnings:
                    for warning in warnings[:5]:  # Show first 5 warnings
                        messages.warning(request, warning)
                    if len(warnings) > 5:
                        messages.warning(request, f"... and {len(warnings) - 5} more warnings")
                
                if errors:
                    for error in errors[:5]:  # Show first 5 errors
                        messages.error(request, error)
                    if len(errors) > 5:
                        messages.error(request, f"... and {len(errors) - 5} more errors")
                
                if imported_count == 0 and (errors or warnings):
                    messages.error(request, "No facilities were imported. Please check the errors above and fix your CSV file.")
                
            except Exception as e:
                messages.error(request, f'Error processing CSV file: {str(e)}')
            
            return redirect('facility_admin:bulk_import')
    else:
        form = BulkImportForm()
    
    return render(request, 'facility_admin/bulk_import.html', {'form': form})


@login_required
@user_passes_test(is_admin)
@require_POST
def bulk_approve(request):
    """Bulk approve multiple pending facilities"""
    
    facility_ids = request.POST.getlist('facility_ids')
    action = request.POST.get('action')
    
    if not facility_ids:
        messages.error(request, 'No facilities selected.')
        return redirect('facility_admin:approval_queue')
    
    facilities = Facility.objects.filter(id__in=facility_ids, status='pending')
    count = 0
    
    for facility in facilities:
        if action == 'approve':
            facility.status = 'active'
            facility.approved_by = request.user
            facility.approved_at = timezone.now()
            facility.save()
            
            # Create bed availability record
            BedAvailability.objects.get_or_create(
                facility=facility,
                defaults={
                    'available_beds': 0,
                    'shared_beds_total': 0,
                    'shared_beds_male': 0,
                    'shared_beds_female': 0,
                    'separate_beds_total': 0,
                    'separate_beds_male': 0,
                    'separate_beds_female': 0,
                }
            )
            
            # Log bulk approval
            FacilityChangeLog.objects.create(
                facility=facility,
                changed_by=request.user,
                change_type='approved',
                old_values={'status': 'pending'},
                new_values={'status': 'active'},
                notes='Bulk approval'
            )
            count += 1
            
        elif action == 'reject':
            facility.status = 'rejected'
            facility.save()
            
            # Log bulk rejection
            FacilityChangeLog.objects.create(
                facility=facility,
                changed_by=request.user,
                change_type='rejected',
                old_values={'status': 'pending'},
                new_values={'status': 'rejected'},
                notes='Bulk rejection'
            )
            count += 1
    
    if action == 'approve':
        messages.success(request, f'Successfully approved {count} facilities!')
    elif action == 'reject':
        messages.warning(request, f'Successfully rejected {count} facilities!')
    
    return redirect('facility_admin:approval_queue')


@login_required
@user_passes_test(is_admin)
def export_facilities(request):
    """Export facilities to CSV"""
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="facilities_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Name', 'Type', 'Endorsement', 'Inspection Number', 'Address', 
        'State', 'County', 'Contact', 'Contact Person', 'Bed Count',
        'Status', 'Available Beds', 'Total Beds (Shared + Private)', 
        'Created At', 'Submitted By'
    ])
    
    # Get facilities based on filters
    facilities = Facility.objects.all().order_by('name')
    
    # Apply filters if provided
    status = request.GET.get('status')
    if status:
        facilities = facilities.filter(status=status)
    
    facility_type = request.GET.get('facility_type')
    if facility_type:
        facilities = facilities.filter(facility_type=facility_type)
    
    # Write data
    for facility in facilities:
        # Get bed information if available
        try:
            bed_info = facility.bed_availability
            available_beds = bed_info.available_beds
            total_beds = bed_info.shared_beds_total + bed_info.separate_beds_total
        except BedAvailability.DoesNotExist:
            available_beds = 'N/A'
            total_beds = 'N/A'
        
        writer.writerow([
            facility.name,
            facility.facility_type,
            facility.endorsement or '',
            facility.inspection_number,
            facility.address,
            facility.state,
            facility.county,
            facility.contact or '',
            facility.contact_person or '',
            facility.bed_count,
            facility.get_status_display(),
            available_beds,
            total_beds,
            facility.created_at.strftime('%Y-%m-%d %H:%M'),
            facility.submitted_by.username if facility.submitted_by else ''
        ])
    
    return response


@login_required
@user_passes_test(is_admin)
def facility_detail_admin(request, facility_id):
    """Admin view of facility details with change history and bed information"""
    
    facility = get_object_or_404(Facility, id=facility_id)
    change_logs = FacilityChangeLog.objects.filter(facility=facility).order_by('-timestamp')
    
    # Get submission details if available
    submission = None
    try:
        submission = facility.facilitysubmission
    except FacilitySubmission.DoesNotExist:
        pass
    
    # Get bed availability information
    bed_info = None
    try:
        bed_info = facility.bed_availability
    except BedAvailability.DoesNotExist:
        pass
    
    context = {
        'facility': facility,
        'change_logs': change_logs,
        'submission': submission,
        'bed_info': bed_info,
    }
    
    return render(request, 'facility_admin/facility_detail.html', context)


@login_required
@user_passes_test(is_admin)
@require_POST
def change_facility_status(request, facility_id):
    """Change facility status via AJAX"""
    
    facility = get_object_or_404(Facility, id=facility_id)
    new_status = request.POST.get('status')
    
    if new_status not in dict(Facility.STATUS_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid status'})
    
    old_status = facility.status
    facility.status = new_status
    facility.save()
    
    # Create bed availability record if activating facility and it doesn't exist
    if new_status == 'active':
        BedAvailability.objects.get_or_create(
            facility=facility,
            defaults={
                'available_beds': 0,
                'shared_beds_total': 0,
                'shared_beds_male': 0,
                'shared_beds_female': 0,
                'separate_beds_total': 0,
                'separate_beds_male': 0,
                'separate_beds_female': 0,
            }
        )
    
    # Log status change
    FacilityChangeLog.objects.create(
        facility=facility,
        changed_by=request.user,
        change_type='status_change',
        old_values={'status': old_status},
        new_values={'status': new_status},
        notes=f'Status changed from {old_status} to {new_status}'
    )
    
    return JsonResponse({
        'success': True, 
        'new_status': facility.get_status_display(),
        'status_value': facility.status
    })
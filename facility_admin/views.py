# facility_admin/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
import csv
import io

from search.models import Facility, FacilitySubmission, FacilityChangeLog
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
    """Admin dashboard with quick stats and recent activity"""
    
    # Quick stats
    stats = {
        'total_facilities': Facility.objects.count(),
        'active_facilities': Facility.objects.filter(status='active').count(),
        'pending_facilities': Facility.objects.filter(status='pending').count(),
        'inactive_facilities': Facility.objects.filter(status='inactive').count(),
    }
    
    # Recent activity
    recent_submissions = Facility.objects.filter(status='pending').order_by('-created_at')[:5]
    recent_changes = FacilityChangeLog.objects.select_related('facility', 'changed_by').order_by('-timestamp')[:10]
    
    context = {
        'stats': stats,
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
    paginator = Paginator(facilities, 20)
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
    """Approve or reject a pending facility"""
    
    facility = get_object_or_404(Facility, id=facility_id, status='pending')
    
    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            admin_notes = form.cleaned_data['admin_notes']
            rejection_reason = form.cleaned_data.get('rejection_reason', '')
            
            if action == 'approve':
                facility.status = 'active'
                facility.approved_by = request.user
                facility.approved_at = timezone.now()
                facility.save()
                
                # Update submission record
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
                    old_values={'status': 'pending'},
                    new_values={'status': 'active'},
                    notes=admin_notes
                )
                
                messages.success(request, f'Facility "{facility.name}" has been approved!')
                
            elif action == 'reject':
                facility.status = 'rejected'
                facility.save()
                
                # Update submission record
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
                    old_values={'status': 'pending'},
                    new_values={'status': 'rejected'},
                    notes=f"Rejection reason: {rejection_reason}"
                )
                
                messages.warning(request, f'Facility "{facility.name}" has been rejected.')
            
            return redirect('facility_admin:approval_queue')
    else:
        form = ApprovalForm()
    
    return render(request, 'facility_admin/facility_approve.html', {
        'facility': facility,
        'form': form
    })


@login_required
@user_passes_test(is_admin)
def bulk_import(request):
    """Bulk import facilities from CSV"""
    
    if request.method == 'POST':
        form = BulkImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            try:
                # Read CSV file
                file_content = csv_file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(file_content))
                
                imported_count = 0
                errors = []
                
                for row_num, row in enumerate(csv_reader, start=2):
                    try:
                        # Create facility from CSV row
                        facility = Facility(
                            name=row['Name'],
                            facility_type=row['Type'],
                            endorsement=row.get('Endorsement', ''),
                            inspection_number=row['Inspection Number'],
                            address=row['Address'],
                            state=row['State'],
                            county=row['County'],
                            contact=row.get('Contact', ''),
                            contact_person=row.get('Contact Person', ''),
                            bed_count=int(row['Bed Count']) if row['Bed Count'] else 0,
                            submitted_by=request.user,
                            submission_type='bulk_import',
                            status='active',  # Bulk imports are immediately active
                            approved_by=request.user,
                            approved_at=timezone.now()
                        )
                        facility.save()
                        
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
                
                if imported_count > 0:
                    messages.success(request, f'Successfully imported {imported_count} facilities!')
                
                if errors:
                    for error in errors[:5]:  # Show first 5 errors
                        messages.error(request, error)
                    if len(errors) > 5:
                        messages.error(request, f"... and {len(errors) - 5} more errors")
                
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
        'Status', 'Created At', 'Submitted By'
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
            facility.created_at.strftime('%Y-%m-%d %H:%M'),
            facility.submitted_by.username if facility.submitted_by else ''
        ])
    
    return response


@login_required
@user_passes_test(is_admin)
def facility_detail_admin(request, facility_id):
    """Admin view of facility details with change history"""
    
    facility = get_object_or_404(Facility, id=facility_id)
    change_logs = FacilityChangeLog.objects.filter(facility=facility).order_by('-timestamp')
    
    # Get submission details if available
    submission = None
    try:
        submission = facility.facilitysubmission
    except FacilitySubmission.DoesNotExist:
        pass
    
    context = {
        'facility': facility,
        'change_logs': change_logs,
        'submission': submission,
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
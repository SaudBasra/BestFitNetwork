from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone  # Import the timezone module
from .forms import BedAvailabilityForm
from search.models import Facility
from .models import BedAvailability
from django.db.models import F, Sum, Value, IntegerField
from django.db.models.functions import Coalesce

def bed_update_view(request):
    facilities = Facility.objects.all().order_by('name')
    selected_facility_id = request.GET.get('facility')
    bed_data = None
    form = None
    facility_bed_count = 0

    if selected_facility_id:
        facility = get_object_or_404(Facility, id=selected_facility_id)
        bed_data, created = BedAvailability.objects.get_or_create(facility=facility)
        facility_bed_count = facility.bed_count  # Get the official bed count from Facility model

        if request.method == 'POST':
            form = BedAvailabilityForm(request.POST, instance=bed_data)
            if form.is_valid():
                bed_update = form.save(commit=False)
                # Explicitly set the updated_at timestamp to current localized time
                bed_update.updated_at = timezone.localtime(timezone.now())
                bed_update.save()
                messages.success(request, f"Bed information for {facility.name} has been updated successfully.")
                return redirect(f'{reverse("bed_update_view")}?facility={facility.id}&updated=success')
        else:
            form = BedAvailabilityForm(instance=bed_data)
            form.fields['facility'].initial = facility

    # Calculate some statistics for dashboard (could be moved to a context processor if used across multiple views)
    context = {
        'facilities': facilities,
        'form': form,
        'selected_facility_id': selected_facility_id,
        'bed_data': bed_data,
        'facility_bed_count': facility_bed_count,  # Pass the official bed count to the template
    }
    
    return render(request, 'bedupdates/bed_update_form.html', context)

# Keeping the existing facility_dashboard_view
def facility_dashboard_view(request):
    """View to show overall dashboard of all facilities"""
    facilities = Facility.objects.all()
    
    # Calculate total official beds from facilities
    total_official_beds = facilities.aggregate(Sum('bed_count'))['bed_count__sum'] or 0
    
    # Get overall statistics
    bed_stats = BedAvailability.objects.aggregate(
        total_beds=Coalesce(Sum(F('shared_beds_total') + F('separate_beds_total')), Value(0), output_field=IntegerField()),
        available_beds=Coalesce(Sum('available_beds'), Value(0), output_field=IntegerField()),
        total_shared=Coalesce(Sum('shared_beds_total'), Value(0), output_field=IntegerField()),
        total_separate=Coalesce(Sum('separate_beds_total'), Value(0), output_field=IntegerField()),
    )
    
    # Get facilities with low bed availability (less than 10% available)
    low_availability = []
    for facility in facilities:
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
    
    context = {
        'bed_stats': bed_stats,
        'facilities': facilities,
        'facility_count': facilities.count(),
        'low_availability': low_availability,
        'total_official_beds': total_official_beds  # Add this to your context
    }
    
    return render(request, 'bedupdates/dashboard.html', context)
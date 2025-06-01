from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import UserTrackingForm
from .models import UserTracking

@require_POST
def submit_user_tracking(request):
    """Handle AJAX submission of user tracking data"""
    form = UserTrackingForm(request.POST)
    if form.is_valid():
        user_tracking = form.save(commit=False)
        user_tracking.search_query = request.POST.get('search_query', '')
        user_tracking.save()
        return JsonResponse({
            'success': True,
            'message': 'Thank you! The results are now available.',
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)

def user_tracking_dashboard(request):
    """Dashboard to view all user tracking data"""
    user_trackings = UserTracking.objects.all()
    total_entries = user_trackings.count()
    joined_facilities = user_trackings.filter(joined_facility=True).count()
    
    # Calculate conversion rate properly
    conversion_rate = (joined_facilities / total_entries * 100) if total_entries > 0 else 0
    
    context = {
        'user_trackings': user_trackings,
        'total_entries': total_entries,
        'joined_facilities': joined_facilities,
        'conversion_rate': conversion_rate,
    }
    return render(request, 'usertracking/dashboard.html', context)

@require_POST
def toggle_tracking_status(request, tracking_id):
    """Toggle the joined_facility status for a tracking record"""
    try:
        tracking = UserTracking.objects.get(id=tracking_id)
        tracking.joined_facility = request.POST.get('joined_facility') == 'true'
        tracking.save()
        return JsonResponse({'success': True})
    except UserTracking.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)
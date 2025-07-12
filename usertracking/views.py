from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from .forms import UserTrackingForm
from .models import UserTracking
import csv
import io

@require_POST
def submit_user_tracking(request):
    """Handle AJAX submission of user tracking data with session management"""
    form = UserTrackingForm(request.POST)
    if form.is_valid():
        user_tracking = form.save(commit=False)
        user_tracking.search_query = request.POST.get('search_query', '')
        user_tracking.save()
        
        # Set session variables for tracking
        request.session['user_tracked'] = True
        request.session['tracking_timestamp'] = timezone.now().isoformat()
        request.session['user_tracking_id'] = user_tracking.id
        
        # Set session expiry to 30 minutes from now
        request.session.set_expiry(30 * 60)  # 30 minutes in seconds
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you! The results are now available.',
            'tracking_status': True
        })
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors,
        }, status=400)

def check_tracking_status(request):
    """Check if user needs to fill tracking form based on session"""
    user_tracked = request.session.get('user_tracked', False)
    tracking_timestamp = request.session.get('tracking_timestamp')
    
    if user_tracked and tracking_timestamp:
        # Parse the timestamp
        from django.utils.dateparse import parse_datetime
        timestamp = parse_datetime(tracking_timestamp)
        
        if timestamp:
            # Check if 30 minutes have passed
            thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
            
            if timestamp > thirty_minutes_ago:
                # User is still within the 30-minute window
                return JsonResponse({
                    'needs_tracking': False,
                    'message': 'User is already tracked',
                    'time_remaining': int((timestamp + timedelta(minutes=30) - timezone.now()).total_seconds())
                })
    
    # Clear expired session data
    if 'user_tracked' in request.session:
        del request.session['user_tracked']
    if 'tracking_timestamp' in request.session:
        del request.session['tracking_timestamp']
    if 'user_tracking_id' in request.session:
        del request.session['user_tracking_id']
    
    return JsonResponse({
        'needs_tracking': True,
        'message': 'User needs to complete tracking form'
    })

@login_required
def user_tracking_dashboard(request):
    """Dashboard to view all user tracking data with export functionality"""
    
    # Check for export request
    if request.GET.get('export') == 'csv':
        return export_user_tracking_csv(request)
    
    # Get all tracking data ordered by most recent
    user_trackings = UserTracking.objects.all().order_by('-timestamp')
    total_entries = user_trackings.count()
    joined_facilities = user_trackings.filter(joined_facility=True).count()
    
    # Calculate conversion rate properly
    conversion_rate = (joined_facilities / total_entries * 100) if total_entries > 0 else 0
    
    # Get recent activity stats (last 24 hours)
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    recent_entries = user_trackings.filter(timestamp__gte=twenty_four_hours_ago).count()
    
    # Get tracking frequency stats
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    daily_stats = user_trackings.filter(timestamp__gte=today_start).count()
    weekly_stats = user_trackings.filter(timestamp__gte=week_start).count()
    monthly_stats = user_trackings.filter(timestamp__gte=month_start).count()
    
    context = {
        'user_trackings': user_trackings,
        'total_entries': total_entries,
        'joined_facilities': joined_facilities,
        'conversion_rate': conversion_rate,
        'recent_entries': recent_entries,
        'daily_stats': daily_stats,
        'weekly_stats': weekly_stats,
        'monthly_stats': monthly_stats,
    }
    return render(request, 'usertracking/dashboard.html', context)

@login_required
def export_user_tracking_csv(request):
    """Export user tracking data to CSV with enhanced filtering"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_tracking_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Name', 'Email', 'Phone', 'Facility Type Interest', 'Zip Code', 
        'Search Query', 'Timestamp', 'Joined Facility', 'Date Created',
        'Time Since Last Tracking', 'Session Duration'
    ])
    
    # Get tracking data based on any filters
    trackings = UserTracking.objects.all().order_by('-timestamp')
    
    # Apply filters if provided in GET parameters
    facility_filter = request.GET.get('facility_type')
    if facility_filter:
        trackings = trackings.filter(facility_type_interest__icontains=facility_filter)
    
    joined_filter = request.GET.get('joined')
    if joined_filter:
        trackings = trackings.filter(joined_facility=joined_filter.lower() == 'true')
    
    date_from = request.GET.get('date_from')
    if date_from:
        trackings = trackings.filter(timestamp__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        trackings = trackings.filter(timestamp__date__lte=date_to)
    
    # Write data with enhanced tracking metrics
    previous_tracking = None
    for tracking in trackings:
        # Calculate time since last tracking by same email
        time_since_last = 'First time'
        if previous_tracking and previous_tracking.email == tracking.email:
            time_diff = tracking.timestamp - previous_tracking.timestamp
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            time_since_last = f"{hours}h {minutes}m"
        
        # Session duration (placeholder - would need session tracking)
        session_duration = 'N/A'
        
        writer.writerow([
            tracking.name,
            tracking.email,
            tracking.phone,
            tracking.facility_type_interest,
            tracking.zip_code,
            tracking.search_query,
            tracking.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'Yes' if tracking.joined_facility else 'No',
            tracking.timestamp.strftime('%Y-%m-%d'),
            time_since_last,
            session_duration
        ])
        
        previous_tracking = tracking
    
    return response

@require_POST
@login_required
def toggle_tracking_status(request, tracking_id):
    """Toggle the joined_facility status for a tracking record"""
    try:
        tracking = UserTracking.objects.get(id=tracking_id)
        # Toggle the status
        tracking.joined_facility = not tracking.joined_facility
        tracking.save()
        
        return JsonResponse({
            'success': True,
            'new_status': tracking.joined_facility,
            'message': f'Status updated to {"Joined" if tracking.joined_facility else "Pending"}'
        })
    except UserTracking.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Record not found'
        }, status=404)

@login_required
def get_tracking_stats(request):
    """API endpoint to get current tracking statistics with session info"""
    total_entries = UserTracking.objects.count()
    joined_facilities = UserTracking.objects.filter(joined_facility=True).count()
    conversion_rate = (joined_facilities / total_entries * 100) if total_entries > 0 else 0
    
    # Recent activity stats (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_entries = UserTracking.objects.filter(timestamp__gte=week_ago).count()
    recent_conversions = UserTracking.objects.filter(
        timestamp__gte=week_ago, 
        joined_facility=True
    ).count()
    
    # Tracking frequency analysis
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    
    today_entries = UserTracking.objects.filter(timestamp__gte=today).count()
    yesterday_entries = UserTracking.objects.filter(
        timestamp__gte=yesterday, 
        timestamp__lt=today
    ).count()
    
    # Calculate average time between tracking submissions
    from django.db.models import Avg
    from django.db import connection
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT AVG(time_diff) as avg_time_diff FROM (
                SELECT 
                    email,
                    timestamp - LAG(timestamp) OVER (PARTITION BY email ORDER BY timestamp) as time_diff
                FROM usertracking_usertracking
                WHERE timestamp >= %s
            ) subquery WHERE time_diff IS NOT NULL
        """, [week_ago])
        
        result = cursor.fetchone()
        avg_time_between_submissions = result[0] if result and result[0] else None
    
    return JsonResponse({
        'total_entries': total_entries,
        'joined_facilities': joined_facilities,
        'conversion_rate': round(conversion_rate, 1),
        'recent_entries': recent_entries,
        'recent_conversions': recent_conversions,
        'today_entries': today_entries,
        'yesterday_entries': yesterday_entries,
        'avg_time_between_submissions': str(avg_time_between_submissions) if avg_time_between_submissions else None
    })

@require_POST
@login_required
def update_tracking_notes(request, tracking_id):
    """Update notes for a specific tracking record"""
    try:
        tracking = UserTracking.objects.get(id=tracking_id)
        notes = request.POST.get('notes', '')
        
        # If your UserTracking model has a notes field, update it
        # tracking.notes = notes
        # tracking.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notes updated successfully'
        })
    except UserTracking.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Record not found'
        }, status=404)

def reset_user_tracking_session(request):
    """Reset user tracking session (useful for testing or manual reset)"""
    if 'user_tracked' in request.session:
        del request.session['user_tracked']
    if 'tracking_timestamp' in request.session:
        del request.session['tracking_timestamp']
    if 'user_tracking_id' in request.session:
        del request.session['user_tracking_id']
    
    return JsonResponse({
        'success': True,
        'message': 'User tracking session reset successfully'
    })

@login_required
def tracking_analytics(request):
    """Advanced analytics for tracking patterns"""
    
    # Get time-based analytics
    now = timezone.now()
    periods = {
        'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
        'week': now - timedelta(days=7),
        'month': now - timedelta(days=30),
        'quarter': now - timedelta(days=90)
    }
    
    analytics = {}
    
    for period_name, start_date in periods.items():
        period_trackings = UserTracking.objects.filter(timestamp__gte=start_date)
        
        analytics[period_name] = {
            'total_submissions': period_trackings.count(),
            'unique_emails': period_trackings.values('email').distinct().count(),
            'conversions': period_trackings.filter(joined_facility=True).count(),
            'top_facility_types': list(
                period_trackings.values('facility_type_interest')
                .annotate(count=models.Count('facility_type_interest'))
                .order_by('-count')[:5]
            ),
            'top_zip_codes': list(
                period_trackings.values('zip_code')
                .annotate(count=models.Count('zip_code'))
                .order_by('-count')[:10]
            )
        }
        
        # Calculate conversion rate
        total = analytics[period_name]['total_submissions']
        conversions = analytics[period_name]['conversions']
        analytics[period_name]['conversion_rate'] = (conversions / total * 100) if total > 0 else 0
    
    # Peak hours analysis
    from django.db.models import Count, Extract
    hourly_distribution = (
        UserTracking.objects
        .filter(timestamp__gte=periods['month'])
        .annotate(hour=Extract('timestamp', 'hour'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )
    
    context = {
        'analytics': analytics,
        'hourly_distribution': list(hourly_distribution),
    }
    
    return render(request, 'usertracking/analytics.html', context)
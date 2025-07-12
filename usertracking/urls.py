# usertracking/urls.py
from django.urls import path
from . import views

app_name = 'usertracking'

urlpatterns = [
    # Your existing URLs (unchanged)
    path('submit/', views.submit_user_tracking, name='submit_user_tracking'),
    path('dashboard/', views.user_tracking_dashboard, name='dashboard'),
    path('export/', views.export_user_tracking_csv, name='export_csv'),
    path('stats/', views.get_tracking_stats, name='get_stats'),  # Note: kept your naming
    path('toggle-status/<int:tracking_id>/', views.toggle_tracking_status, name='toggle_status'),
    path('update-notes/<int:tracking_id>/', views.update_tracking_notes, name='update_notes'),
    
    # New optional URLs (extra functionality)
    path('check-status/', views.check_tracking_status, name='check_tracking_status'),
    path('reset-session/', views.reset_user_tracking_session, name='reset_tracking_session'),
    path('analytics/', views.tracking_analytics, name='analytics'),
]
# bedupdates/urls.py - Complete URL configuration

from django.urls import path
from . import views

app_name = 'bedupdates'

urlpatterns = [
    # Main bed management dashboard
    path('', views.facility_dashboard_view, name='dashboard'),
    path('management/', views.facility_bed_management, name='bed_management'),
    path('management/<int:facility_id>/', views.facility_bed_management, name='bed_management'),
    
    # Facility configuration wizard URLs
    path('configure/<int:facility_id>/', views.configure_facility, name='configure_facility'),
    path('reconfigure/<int:facility_id>/', views.reconfigure_facility, name='reconfigure_facility'),
    
    # AJAX endpoints for bed management
    path('api/update-bed-status/', views.update_bed_status, name='update_bed_status'),
    
    # Legacy URLs for backward compatibility
    path('update/', views.bed_update_view, name='bed_update_view'),
    path('update/<int:facility_id>/', views.bed_update_view, name='bed_update_facility'),
    path('dashboard/', views.facility_dashboard_view, name='facility_dashboard'),
]
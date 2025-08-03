# user_management/urls.py - Updated for credential number system

from django.urls import path
from . import views

app_name = 'user_management'

urlpatterns = [
    # Login and authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Facility staff dashboard and management
    path('facility-dashboard/', views.facility_dashboard, name='facility_dashboard'),
    path('facility-detail/', views.facility_detail_staff, name='facility_detail_staff'),
    path('facility-update/', views.facility_update_staff, name='facility_update_staff'),
    path('facility-bed-update/', views.facility_bed_update_staff, name='facility_bed_update_staff'),
    
    # User profile and session management
    path('profile/', views.user_profile, name='profile'),
    path('sessions/', views.user_sessions, name='user_sessions'),
    path('sessions/<int:session_id>/terminate/', views.terminate_session, name='terminate_session'),
    
    # API endpoints - Updated for credential number system
    path('api/validate-facility-registration/', views.validate_facility_api, name='validate_facility_registration'),
    path('api/update-session-activity/', views.update_session_activity, name='update_session_activity'),


   # NEW: Pricing Management URLs
    path('facility-pricing/', views.facility_pricing_management, name='facility_pricing_management'),
    path('facility-pricing-preview/', views.facility_pricing_preview, name='facility_pricing_preview'),
 
]
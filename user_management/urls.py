# user_management/urls.py

from django.urls import path
from . import views

app_name = 'user_management'

urlpatterns = [
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    
    # Dashboard URLs
    path('facility-dashboard/', views.facility_dashboard, name='facility_dashboard'),
    path('profile/', views.user_profile, name='profile'),
    
    # Facility Staff URLs
    path('facility-details/', views.facility_detail_staff, name='facility_detail_staff'),
    path('facility-update/', views.facility_update_staff, name='facility_update_staff'),
    path('facility-bed-management/', views.facility_bed_update_staff, name='facility_bed_update_staff'),
    
    # Session Management URLs
    path('sessions/', views.user_sessions, name='user_sessions'),
    path('terminate-session/<int:session_id>/', views.terminate_session, name='terminate_session'),
    path('api/update-session-activity/', views.update_session_activity, name='update_session_activity'),
    
    # API URLs for facility validation
    path('api/validate-facility/', views.validate_facility_api, name='validate_facility_api'),
]
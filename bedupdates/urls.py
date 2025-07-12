# bedupdates/urls.py - Updated for better integration
from django.urls import path
from . import views

# Using app_name for namespace consistency
app_name = 'bedupdates'

urlpatterns = [
    # Bed dashboard - overview of all bed availability
    path('dashboard/', views.facility_dashboard_view, name='facility_dashboard'),

    # Update bed information form
    path('update/', views.bed_update_view, name='bed_update_view'),

    # Quick update for specific facility (with facility ID in URL)
    path('update/<int:facility_id>/', views.bed_update_view, name='bed_update_facility'),

    # API endpoint for AJAX bed updates (optional)
    # path('api/update/', views.bed_update_api, name='bed_update_api'),

    # Export bed data as CSV
    # path('export/', views.export_bed_data, name='export_bed_data'),
]
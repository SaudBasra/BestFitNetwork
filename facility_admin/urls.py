# facility_admin/urls.py
from django.urls import path
from . import views

app_name = 'facility_admin'

urlpatterns = [
    # Dashboard
    path('', views.admin_dashboard, name='dashboard'),
    
    # Facility CRUD
    path('facilities/', views.facility_list, name='facility_list'),
    path('facilities/create/', views.facility_create, name='facility_create'),
    path('facilities/<int:facility_id>/edit/', views.facility_edit, name='facility_edit'),
    path('facilities/<int:facility_id>/detail/', views.facility_detail_admin, name='facility_detail'),
    path('facilities/<int:facility_id>/status/', views.change_facility_status, name='change_status'),
    
    # Approval workflow
    path('approvals/', views.approval_queue, name='approval_queue'),
    path('approvals/<int:facility_id>/', views.facility_approve, name='facility_approve'),
    path('approvals/bulk/', views.bulk_approve, name='bulk_approve'),
    
    # Bulk operations
    path('import/', views.bulk_import, name='bulk_import'),
    path('export/', views.export_facilities, name='export_facilities'),
    
    # Public registration
    path('register/', views.public_registration, name='public_registration'),
]
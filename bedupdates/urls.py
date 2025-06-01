# urls.py - Add new URLs for the dashboard
from django.urls import path
from . import views

urlpatterns = [
    path('update-bed-info/', views.bed_update_view, name='bed_update_view'),
    path('dashboard/', views.facility_dashboard_view, name='facility_dashboard'),
    path('', views.facility_dashboard_view, name='home'),  # Make dashboard the home page
]
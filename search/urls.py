# search/urls.py - Enhanced version with all features

from django.urls import path
from . import views

app_name = 'search' 

urlpatterns = [
    # Enhanced Template Views - Primary routes
    path('', views.home, name='home'),  # Enhanced home with Ollama AI + Images + User Tracking
    path('facility/<int:facility_id>/', views.facility_detail, name='facility_detail'),

    # Legacy/Alternative routes for backward compatibility
    path('searxng/', views.searxnghome, name='searxng_home'),
    path('searxng/facility/<int:facility_id>/', views.searxngfacilitydetail, name='searxngfacilitydetail'),
    
    # Ollama search route (legacy - functionality now in main home)
    path('ollama/', views.ollama_search, name='ollama_search'),
]
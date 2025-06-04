# search/urls.py - Fixed version without missing views

from django.urls import path
from . import views
app_name = 'search' 
urlpatterns = [
    # Template Views
    path('', views.home, name='home'),
    path('facility/<int:facility_id>/', views.facility_detail, name='facility_detail'),

    # Searxng routes
    path('searxng/', views.searxnghome, name='searxng_home'),
    path('searxng/facility/<int:facility_id>/', views.searxngfacilitydetail, name='searxngfacilitydetail'),
    
    # Remove the problematic line that references missing facility_insights_api
    # path('searxng/api/facility_insights/<str:facility_name>/', views.facility_insights_api, name='facility_insights_api'),

    # Keep the working facility detail route
    # path('facility/<int:facility_id>/', views.facility_detail, name='facility_detail'),
    
    # Remove duplicate/conflicting routes
    # path('api/insights/<str:facility_name>/', views.facility_insights_api, name='facility_insights'),
    # path('facility/<int:facility_id>/', views.facility_detail, name='facility_detail'),
    # path('api/insights/<str:facility_name>/', views.facility_insights_api, name='facility_insights_api'),

    # Ollama search route
    path('ollama/', views.ollama_search, name='ollama_search'),
]





"""
from django.urls import path
from . import views

urlpatterns = [
 
    # Template Views
    path('', views.home, name='home'),
    path('facility/<int:facility_id>/', views.facility_detail, name='facility_detail'),



 
    # Searxng routes
    path('searxng/', views.searxnghome, name='searxng_home'),
     path('searxng/facility/<int:facility_id>/', views.searxngfacilitydetail, name='searxngfacilitydetail'),
    path('searxng/api/facility_insights/<str:facility_name>/', views.facility_insights_api, name='facility_insights_api'),

    path('facility/<int:facility_id>/', views.searxngfacilitydetail, name='facility_detail'),
    path('api/insights/<str:facility_name>/', views.facility_insights_api, name='facility_insights'),


   path('facility/<int:facility_id>/', views.searxngfacilitydetail, name='facility_detail'),
    path('api/insights/<str:facility_name>/', views.facility_insights_api, name='facility_insights_api'),

    #path('searxng/', views.searxng, name='searxng'),
    #path('perplexica/', views.perplexica, name='perplexica'),
    #path('combined/', views.combined, name='combined'),
     path('ollama/', views.ollama_search, name='ollama_search'),
  
#    path('ollama/', views.ollama_search_view, name='ollama_search'),

   
        # API Endpoints
   # path('api/facilities/', views.facility_list, name='facility_list'),
   # path('api/facilities/<int:pk>/', views.api_facility_detail, name='api_facility_detail'),
   # path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
   
]

"""

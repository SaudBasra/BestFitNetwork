# facility_landing/urls.py

from django.urls import path
from . import views

app_name = 'facility_landing'

urlpatterns = [
    # Public landing page - make this more specific to avoid conflicts
    path('landing/<int:facility_id>/', views.public_landing_page, name='public_page'),
    path('landing/<int:facility_id>/preview/', views.preview_landing_page, name='preview_page'),
    
    # Staff management URLs
    path('landing/dashboard/', views.landing_page_dashboard, name='dashboard'),
    path('landing/dashboard/edit/', views.edit_landing_page, name='edit_page'),
    path('landing/dashboard/edit/<int:facility_id>/', views.edit_landing_page, name='edit_page_with_id'),
    
    # Gallery management
    path('landing/dashboard/gallery/', views.manage_gallery, name='manage_gallery'),
    path('landing/dashboard/gallery/delete/<int:image_id>/', views.delete_gallery_image, name='delete_gallery_image'),
    
    # Testimonial management
    path('landing/dashboard/testimonials/', views.manage_testimonials, name='manage_testimonials'),
    path('landing/dashboard/testimonials/toggle-featured/<int:testimonial_id>/', views.toggle_testimonial_featured, name='toggle_testimonial_featured'),
    
    # Analytics
    path('landing/dashboard/analytics/', views.landing_page_analytics, name='analytics'),
    
    # AJAX endpoints
    path('landing/api/update-image-order/', views.update_image_order, name='update_image_order'),
# facility_landing/urls.py (add this temporarily)
path('facility/<int:facility_id>/test/', views.test_landing_page, name='test_page'),
]
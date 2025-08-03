# config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.urls import path
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('search.urls', namespace='search')),
    path('', include('facility_landing.urls')),

    path('search/', include('search.urls', namespace='search')),
    path('user-tracking/', include('usertracking.urls')),
    path('usertracking/', include('usertracking.urls', namespace='usertracking')),
    path('facility-admin/', include('facility_admin.urls')),  # Add this
    path('user-management/', include('user_management.urls')),
    path('beds/', include('bedupdates.urls')),

    path('bed-management/', include('bedupdates.urls')),  # Add this



   # Authentication URLs
#    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
#   path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),




]

# Add media files serving for development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

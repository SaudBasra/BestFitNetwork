# facility_landing/apps.py

from django.apps import AppConfig


class FacilityLandingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'facility_landing'
    verbose_name = 'Facility Landing Pages'
    
    def ready(self):
        # Import signals to ensure they're connected
        import facility_landing.models
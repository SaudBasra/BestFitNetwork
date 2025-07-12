# facility_landing/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from search.models import Facility
from .models import FacilityLandingPage


@receiver(post_save, sender=Facility)
def create_default_landing_page(sender, instance, created, **kwargs):
    """
    Automatically create a default landing page when a new facility is created
    """
    if created:
        # Check if landing page already exists (in case of duplicate signals)
        if not hasattr(instance, 'landing_page'):
            FacilityLandingPage.objects.create(
                facility=instance,
                hero_tagline=f"Welcome to {instance.name}",
                hero_description=f"Quality care and comfortable living at {instance.name}, located in {instance.county}, {instance.state}.",
                mission_statement="Our mission is to provide exceptional care and support to our residents in a warm, welcoming environment where dignity and independence are respected.",
                facility_story=f"Established to serve the {instance.county} community, {instance.name} has been committed to providing quality healthcare services. Our dedicated team works tirelessly to ensure each resident receives personalized care tailored to their individual needs.",
                services_description=f"At {instance.name}, we offer comprehensive care services including skilled nursing, rehabilitation therapy, memory care, and long-term care. Our {instance.facility_type} specializes in {instance.endorsement or 'general healthcare'} with a focus on maintaining the highest standards of care.",
                specialized_care=f"We provide specialized care programs tailored to our residents' unique needs, including {instance.endorsement or 'comprehensive healthcare services'}.",
                accreditations="Our facility maintains all required state certifications and adheres to the highest standards of healthcare delivery.",
                amenities="• Comfortable private and shared rooms\n• Nutritious meal programs\n• Activity and recreation programs\n• 24/7 skilled nursing care\n• Physical therapy services\n• Beautiful common areas and outdoor spaces",
                staff_credentials="Our team consists of licensed healthcare professionals, including registered nurses, certified nursing assistants, and specialized therapists, all committed to providing compassionate care.",
                visiting_hours="Daily 9:00 AM - 8:00 PM",
                tour_available=True,
                meta_title=f"{instance.name} - Quality Healthcare Facility",
                meta_description=f"Learn more about {instance.name}, a {instance.facility_type} providing quality healthcare services in {instance.county}, {instance.state}.",
                is_published=True
            )
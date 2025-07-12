from django.db import models
from search.models import Facility

class BedAvailability(models.Model):
    facility = models.OneToOneField(Facility, on_delete=models.CASCADE, related_name='bed_availability')
    available_beds = models.IntegerField(default=0)

    shared_beds_total = models.IntegerField(default=0)
    shared_beds_male = models.IntegerField(default=0)
    shared_beds_female = models.IntegerField(default=0)

    separate_beds_total = models.IntegerField(default=0)
    separate_beds_male = models.IntegerField(default=0)
    separate_beds_female = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bed Info for {self.facility.name}"
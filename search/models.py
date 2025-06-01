from django.db import models

class Facility(models.Model):
    name = models.CharField(max_length=255)
    facility_type = models.CharField(max_length=255)
    endorsement = models.CharField(max_length=255, blank=True, null=True)
    inspection_number = models.CharField(max_length=100, unique=True)
    address = models.TextField()
    state = models.CharField(max_length=50)
    county = models.CharField(max_length=100)
    contact = models.CharField(max_length=255, blank=True, null=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    bed_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name


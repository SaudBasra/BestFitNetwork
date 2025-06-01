# usertracking/models.py
from django.db import models
from django.utils import timezone

class UserTracking(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    facility_type_interest = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=10)
    search_query = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    joined_facility = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.email} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['-timestamp']

# facility_admin/models.py
from django.db import models
# Import the enhanced models from search app
# We'll extend Facility model functionality here if needed
from django.urls import reverse

class AdminProfile(models.Model):
    """Extended profile for admin users"""
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=[
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer')
    ], default='admin')
    permissions = models.JSONField(default=dict)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
    

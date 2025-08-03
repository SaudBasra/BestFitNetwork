# bedupdates/models.py - Updated models for room-based bed management

from django.db import models
from search.models import Facility
from django.core.validators import MinValueValidator
import json

class FacilityConfiguration(models.Model):
    """Stores facility room and bed configuration"""
    facility = models.OneToOneField(Facility, on_delete=models.CASCADE, related_name='facility_configuration')
    is_configured = models.BooleanField(default=False)
    total_rooms = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    configuration_data = models.JSONField(default=dict)  # Stores room configuration
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Configuration for {self.facility.name}"
    
    def get_rooms(self):
        """Get rooms from configuration data"""
        return self.configuration_data.get('rooms', [])
    
    def set_rooms(self, rooms):
        """Set rooms in configuration data"""
        if not self.configuration_data:
            self.configuration_data = {}
        self.configuration_data['rooms'] = rooms
    
    def get_total_beds(self):
        """Calculate total beds from all rooms"""
        rooms = self.get_rooms()
        return sum(len(room.get('beds', [])) for room in rooms)
    
    def get_bed_counts_by_type(self):
        """Get bed counts by room type"""
        rooms = self.get_rooms()
        private_beds = 0
        shared_beds = 0
        
        for room in rooms:
            if room.get('type') == 'private':
                private_beds += len(room.get('beds', []))
            else:
                shared_beds += len(room.get('beds', []))
        
        return {
            'private_beds': private_beds,
            'shared_beds': shared_beds,
            'total_beds': private_beds + shared_beds
        }

class Room(models.Model):
    """Individual room within a facility"""
    ROOM_TYPES = [
        ('private', 'Private Room'),
        ('shared', 'Shared Room'),
    ]
    
    GENDER_TYPES = [
        ('neutral', 'Neutral'),
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    facility_config = models.ForeignKey(FacilityConfiguration, on_delete=models.CASCADE, related_name='rooms')
    room_name = models.CharField(max_length=100)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES)
    room_number = models.CharField(max_length=20, blank=True)  # Auto-generated or user-defined
    room_gender = models.CharField(max_length=10, choices=GENDER_TYPES, default='neutral')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['facility_config', 'room_name']
        ordering = ['room_name']
    
    def __str__(self):
        return f"{self.room_name} ({self.get_room_type_display()})"
    
    def get_total_beds(self):
        """Get total beds in this room"""
        return self.beds.count()
    
    def get_occupied_beds(self):
        """Get number of occupied beds"""
        return self.beds.filter(status='occupied').count()
    
    def get_vacant_beds(self):
        """Get number of vacant beds"""
        return self.beds.filter(status='vacant').count()
    
    def update_room_gender_from_occupancy(self):
        """Update room gender based on occupancy for shared rooms"""
        if self.room_type == 'shared':
            occupied_beds = self.beds.filter(status='occupied')
            if occupied_beds.exists():
                # Set room gender based on first occupied bed
                first_occupied = occupied_beds.first()
                if first_occupied.gender != 'neutral':
                    self.room_gender = first_occupied.gender
                    # Update all other beds to same gender but vacant
                    self.beds.exclude(id=first_occupied.id).update(
                        gender=first_occupied.gender,
                        status='vacant'
                    )
            else:
                # No occupied beds, reset to neutral
                self.room_gender = 'neutral'
                self.beds.update(gender='neutral')
            
            self.save()

class Bed(models.Model):
    """Individual bed within a room"""
    BED_STATUS = [
        ('vacant', 'Vacant'),
        ('occupied', 'Occupied'),
    ]
    
    GENDER_TYPES = [
        ('neutral', 'Neutral'),
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.CharField(max_length=10)
    bed_id = models.CharField(max_length=50, unique=True)  # Format: room_name-bed_number
    status = models.CharField(max_length=10, choices=BED_STATUS, default='vacant')
    gender = models.CharField(max_length=10, choices=GENDER_TYPES, default='neutral')
    patient_name = models.CharField(max_length=100, blank=True)  # Optional patient tracking
    admitted_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['room', 'bed_number']
        ordering = ['bed_number']
    
    def __str__(self):
        return f"{self.room.room_name} - Bed {self.bed_number}"
    
    def save(self, *args, **kwargs):
        # Auto-generate bed_id
        if not self.bed_id:
            self.bed_id = f"{self.room.room_name}-{self.bed_number}"
        
        super().save(*args, **kwargs)
        
        # Update room gender based on occupancy changes
        if self.room.room_type == 'shared':
            self.room.update_room_gender_from_occupancy()

# Legacy model for backward compatibility - can be removed after migration
class BedAvailability(models.Model):
    """Legacy model - keeping for backward compatibility"""
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
        return f"Legacy Bed Info for {self.facility.name}"
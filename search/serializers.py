from rest_framework import serializers
from .models import Facility

class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            'id', 'name', 'facility_type', 'endorsement',
            'inspection_number', 'address', 'state',
            'county', 'contact', 'contact_person', 'bed_count'
        ]
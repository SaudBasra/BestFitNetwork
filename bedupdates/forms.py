# bedupdates/forms.py - Updated forms for room-based bed management

from django import forms
from django.core.validators import MinValueValidator
from search.models import Facility
from .models import FacilityConfiguration, Room, Bed

class RoomConfigurationForm(forms.Form):
    """Form for configuring individual rooms"""
    
    ROOM_TYPES = [
        ('private', 'Private Room (1 bed, any gender)'),
        ('shared', 'Shared Room (2+ beds, same gender only)'),
    ]
    
    room_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter room name (e.g., ICU Ward 1, Room 101)'
        }),
        help_text="Enter a unique name for this room"
    )
    
    room_type = forms.ChoiceField(
        choices=ROOM_TYPES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text="Private rooms have 1 bed for any gender. Shared rooms have multiple beds for same gender only."
    )
    
    num_beds = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Number of beds'
        }),
        validators=[MinValueValidator(1)],
        help_text="Private rooms: exactly 1 bed. Shared rooms: 2 or more beds."
    )
    
    def __init__(self, *args, **kwargs):
        self.room_number = kwargs.pop('room_number', None)
        self.existing_room_names = kwargs.pop('existing_room_names', [])
        super().__init__(*args, **kwargs)
    
    def clean_room_name(self):
        room_name = self.cleaned_data.get('room_name', '').strip()
        
        if not room_name:
            raise forms.ValidationError("Room name is required.")
        
        if room_name in self.existing_room_names:
            raise forms.ValidationError("This room name already exists. Please choose a different name.")
        
        return room_name
    
    def clean(self):
        cleaned_data = super().clean()
        room_type = cleaned_data.get('room_type')
        num_beds = cleaned_data.get('num_beds')
        
        if room_type == 'private' and num_beds != 1:
            self.add_error('num_beds', 'Private rooms must have exactly 1 bed.')
        
        if room_type == 'shared' and num_beds < 2:
            self.add_error('num_beds', 'Shared rooms must have at least 2 beds.')
        
        return cleaned_data

class BedUpdateForm(forms.ModelForm):
    """Form for updating individual bed status"""
    
    class Meta:
        model = Bed
        fields = ['status', 'gender', 'patient_name', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'patient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Patient name (optional)'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If this is a shared room, add validation info
        if self.instance and self.instance.room.room_type == 'shared':
            self.fields['gender'].help_text = (
                "In shared rooms, all beds must be the same gender when occupied. "
                f"Current room gender: {self.instance.room.get_room_gender_display()}"
            )

class FacilityConfigurationForm(forms.ModelForm):
    """Form for basic facility configuration"""
    
    class Meta:
        model = FacilityConfiguration
        fields = ['total_rooms']
        widgets = {
            'total_rooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Enter total number of rooms'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.facility = kwargs.pop('facility', None)
        super().__init__(*args, **kwargs)
        
        self.fields['total_rooms'].help_text = (
            f"Official bed count for this facility: {self.facility.bed_count if self.facility else 'N/A'}"
        )
    
    def clean_total_rooms(self):
        total_rooms = self.cleaned_data.get('total_rooms')
        
        if total_rooms <= 0:
            raise forms.ValidationError("Total rooms must be greater than 0.")
        
        # Optional validation against facility bed count
        if self.facility and self.facility.bed_count > 0:
            if total_rooms > self.facility.bed_count:
                raise forms.ValidationError(
                    f"Number of rooms ({total_rooms}) cannot exceed facility bed count ({self.facility.bed_count}). "
                    "Each room must have at least 1 bed."
                )
        
        return total_rooms

# Legacy form for backward compatibility
class BedAvailabilityForm(forms.Form):
    """Legacy form - keeping for backward compatibility"""
    
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.all().order_by('name'),
        widget=forms.HiddenInput(),
        required=True
    )
    
    available_beds = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter number of available beds'
        }),
        validators=[MinValueValidator(0)]
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text for migration
        self.fields['available_beds'].help_text = (
            "Note: This is the legacy bed management system. "
            "Consider migrating to the new room-based system for better management."
        )
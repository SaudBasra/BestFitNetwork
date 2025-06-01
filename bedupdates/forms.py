from django import forms
from .models import BedAvailability
from search.models import Facility
from django.core.validators import MinValueValidator

class BedAvailabilityForm(forms.ModelForm):
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
    
    shared_beds_total = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter total shared beds'
        }),
        validators=[MinValueValidator(0)]
    )
    
    shared_beds_male = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter male shared beds'
        }),
        validators=[MinValueValidator(0)]
    )
    
    shared_beds_female = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter female shared beds'
        }),
        validators=[MinValueValidator(0)]
    )
    
    separate_beds_total = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter total private beds'
        }),
        validators=[MinValueValidator(0)]
    )
    
    separate_beds_male = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter male private beds'
        }),
        validators=[MinValueValidator(0)]
    )
    
    separate_beds_female = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter female private beds'
        }),
        validators=[MinValueValidator(0)]
    )
    
    class Meta:
        model = BedAvailability
        exclude = ['updated_at']
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Get facility to check against official bed count
        facility = cleaned_data.get('facility')
        if facility:
            official_bed_count = facility.bed_count
        else:
            official_bed_count = 0
        
        # Validate that male + female beds don't exceed total beds
        shared_total = cleaned_data.get('shared_beds_total', 0)
        shared_male = cleaned_data.get('shared_beds_male', 0)
        shared_female = cleaned_data.get('shared_beds_female', 0)
        
        if shared_male + shared_female > shared_total:
            self.add_error('shared_beds_male', 'Male and female shared beds cannot exceed total shared beds')
            self.add_error('shared_beds_female', 'Male and female shared beds cannot exceed total shared beds')
        
        separate_total = cleaned_data.get('separate_beds_total', 0)
        separate_male = cleaned_data.get('separate_beds_male', 0)
        separate_female = cleaned_data.get('separate_beds_female', 0)
        
        if separate_male + separate_female > separate_total:
            self.add_error('separate_beds_male', 'Male and female private beds cannot exceed total private beds')
            self.add_error('separate_beds_female', 'Male and female private beds cannot exceed total private beds')
        
        # Validate that total beds don't exceed official bed count
        total_beds = shared_total + separate_total
        if total_beds > official_bed_count:
            self.add_error('shared_beds_total', f'Total beds cannot exceed facility official bed count of {official_bed_count}')
            self.add_error('separate_beds_total', f'Total beds cannot exceed facility official bed count of {official_bed_count}')
        
        # Validate that available beds don't exceed total beds
        available_beds = cleaned_data.get('available_beds', 0)
        if available_beds > total_beds:
            self.add_error('available_beds', 'Available beds cannot exceed total beds (shared + private)')
        
        return cleaned_data
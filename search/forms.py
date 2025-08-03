# search/forms.py - Create this file or add to existing
from django import forms
from .models import FacilityPricing

class FacilityPricingForm(forms.ModelForm):
    """Form for facility staff to manage pricing"""
    
    class Meta:
        model = FacilityPricing
        fields = [
            'private_bed_min_price',
            'private_bed_max_price', 
            'shared_bed_min_price',
            'shared_bed_max_price',
            'notes'
        ]
        
        labels = {
            'private_bed_min_price': 'Private Bed - Minimum Price',
            'private_bed_max_price': 'Private Bed - Maximum Price',
            'shared_bed_min_price': 'Shared Bed - Minimum Price',
            'shared_bed_max_price': 'Shared Bed - Maximum Price',
            'notes': 'Additional Notes'
        }
        
        widgets = {
            'private_bed_min_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2000',
                'step': '0.01',
                'min': '0'
            }),
            'private_bed_max_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '3500',
                'step': '0.01',
                'min': '0'
            }),
            'shared_bed_min_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1200',
                'step': '0.01',
                'min': '0'
            }),
            'shared_bed_max_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '2000',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional pricing information, conditions, or notes for potential residents...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for each field
        self.fields['private_bed_min_price'].help_text = "Lowest monthly rate for private rooms"
        self.fields['private_bed_max_price'].help_text = "Highest monthly rate for private rooms"
        self.fields['shared_bed_min_price'].help_text = "Lowest monthly rate for shared rooms"
        self.fields['shared_bed_max_price'].help_text = "Highest monthly rate for shared rooms"
        self.fields['notes'].help_text = "Any additional information about pricing, services included, or special conditions"
    
    def clean(self):
        """Custom validation for pricing ranges"""
        cleaned_data = super().clean()
        
        private_min = cleaned_data.get('private_bed_min_price')
        private_max = cleaned_data.get('private_bed_max_price')
        shared_min = cleaned_data.get('shared_bed_min_price')
        shared_max = cleaned_data.get('shared_bed_max_price')
        
        # Validate private bed pricing
        if private_min and private_max and private_min > private_max:
            raise forms.ValidationError({
                'private_bed_max_price': 'Maximum price cannot be less than minimum price for private beds.'
            })
        
        # Validate shared bed pricing
        if shared_min and shared_max and shared_min > shared_max:
            raise forms.ValidationError({
                'shared_bed_max_price': 'Maximum price cannot be less than minimum price for shared beds.'
            })
        
        # Ensure at least some pricing info is provided
        if not any([private_min, private_max, shared_min, shared_max]):
            raise forms.ValidationError(
                'Please provide at least one pricing value to save pricing information.'
            )
        
        return cleaned_data
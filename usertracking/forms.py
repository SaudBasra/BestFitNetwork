# usertracking/forms.py
from django import forms
from .models import UserTracking

class UserTrackingForm(forms.ModelForm):
    class Meta:
        model = UserTracking
        fields = ['name', 'email', 'phone', 'facility_type_interest', 'zip_code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Phone Number'}),
            'facility_type_interest': forms.Select(attrs={'class': 'form-control'}, 
                                                choices=[
                                                    ('', 'Select Facility Type'),
                                                    ('ALZHEIMER DISEASE', 'Alzheimer Disease'),
                                                    ('ASSISTED LIVING SERVICES', 'Assisted Living'),
                                                    ('INDIVIDUALS WITH INTELLECTUAL DISABILITES', 'Intellectual Disabilities'),
                                                    ('MENTAL ILLNESS', 'Mental Illness'),
                                                    ('RESIDENTIAL FACILITY FOR ELDERLY OR DISABLED PERSONS', 'Elderly/Disabled Care')
                                                ]),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip Code of Interest'})
        }
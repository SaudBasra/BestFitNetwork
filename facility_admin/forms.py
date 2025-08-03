# facility_admin/forms.py - Complete file updated for credential number system

from django import forms
from search.models import Facility
from django.core.exceptions import ValidationError
import csv
import io
import re

class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = [
            'name', 'facility_type', 'endorsement', 'credential_number',
            'address', 'state', 'county', 'contact', 'contact_person',
            'bed_count', 'image', 'meta_description', 'search_keywords'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Facility Name'}),
            'facility_type': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('ALZHEIMER DISEASE', 'Alzheimer Disease'),
                ('ASSISTED LIVING SERVICES', 'Assisted Living Services'),
                ('INDIVIDUALS WITH INTELLECTUAL DISABILITES', 'Intellectual Disabilities'),
                ('MENTAL ILLNESS', 'Mental Illness'),
                ('RESIDENTIAL FACILITY FOR ELDERLY OR DISABLED PERSONS', 'Elderly/Disabled Care'),
            ]),
            'endorsement': forms.TextInput(attrs={'class': 'form-control'}),
            'credential_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 23242 or 23242-AGC-2',
                'title': 'Enter 2-5 digits or full format (XXXXX-AGC-X)'
            }),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'county': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'bed_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'maxlength': 160}),
            'search_keywords': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_credential_number(self):
        credential_number = self.cleaned_data['credential_number'].strip()
        
        # Normalize the input
        normalized_credential = Facility.normalize_credential_input(credential_number)
        
        # Validate format
        if not Facility.is_valid_credential_format(normalized_credential):
            raise ValidationError('Invalid format. Enter 2-5 digits (e.g., 23242) or full format (e.g., 23242-AGC-2)')
        
        # Check for duplicates using the registration number part
        registration_number = Facility.extract_registration_number(normalized_credential)
        existing_facility = Facility.find_by_registration_number(registration_number)
        
        if existing_facility and (not self.instance.pk or existing_facility.pk != self.instance.pk):
            raise ValidationError(f'A facility with credential number {registration_number} already exists.')
        
        return normalized_credential


class PublicRegistrationForm(forms.ModelForm):
    # Credential number field for public - accepts 2-5 digits (the essential part)
    credential_number = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 2-5 digits (e.g., 23242)',
            'pattern': r'\d{2,5}',
            'title': 'Enter 2-5 digits of your credential number'
        }),
        help_text="Enter your facility credential number (2-5 digits only)"
    )
    
    submitter_name = forms.CharField(
        max_length=255, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    
    submitter_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com'
        })
    )
    
    submitter_phone = forms.CharField(
        max_length=20, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(555) 123-4567'
        })
    )
    
    submission_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Any additional information about your facility...'
        }),
        required=False,
        help_text="Any additional information about your facility or special requirements"
    )

    class Meta:
        model = Facility
        fields = [
            'name', 'facility_type', 'endorsement', 'credential_number',
            'address', 'state', 'county', 'contact', 'contact_person',
            'bed_count', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your facility name'
            }),
            'facility_type': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('', 'Select facility type...'),
                ('ALZHEIMER DISEASE', 'Alzheimer Disease'),
                ('ASSISTED LIVING SERVICES', 'Assisted Living Services'),
                ('INDIVIDUALS WITH INTELLECTUAL DISABILITES', 'Intellectual Disabilities'),
                ('MENTAL ILLNESS', 'Mental Illness'),
                ('RESIDENTIAL FACILITY FOR ELDERLY OR DISABLED PERSONS', 'Elderly/Disabled Care'),
            ]),
            'endorsement': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Memory Care, Physical Therapy, etc.'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Enter complete facility address'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter state'
            }),
            'county': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter county'
            }),
            'contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(555) 123-4567'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter primary contact person name'
            }),
            'bed_count': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0,
                'placeholder': 'Number of beds'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control', 
                'accept': 'image/*'
            }),
        }

    def clean_credential_number(self):
        credential_number = self.cleaned_data['credential_number'].strip()
        
        # Validate format (2-5 digits)
        if not re.match(r'^\d{2,5}$', credential_number):
            raise ValidationError('Credential number must be 2-5 digits only.')
        
        # Check if any facility has this credential number
        existing = Facility.objects.filter(
            credential_number__startswith=f"{credential_number}-AGC"
        ).first()
        
        if not existing:
            # Also check for exact match (simple format)
            existing = Facility.objects.filter(credential_number=credential_number).first()
        
        if existing:
            raise ValidationError(f'A facility with credential number {credential_number} already exists.')
        
        return credential_number
    
    def clean_contact(self):
        """Validate phone number format"""
        contact = self.cleaned_data.get('contact')
        if contact:
            # Remove non-digit characters for validation
            digits_only = ''.join(filter(str.isdigit, contact))
            if len(digits_only) < 10:
                raise ValidationError("Please enter a valid phone number with at least 10 digits.")
        return contact
    
    def clean_submitter_phone(self):
        """Validate submitter phone number format"""
        phone = self.cleaned_data.get('submitter_phone')
        if phone:
            # Remove non-digit characters for validation
            digits_only = ''.join(filter(str.isdigit, phone))
            if len(digits_only) < 10:
                raise ValidationError("Please enter a valid phone number with at least 10 digits.")
        return phone
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Store the credential number (essential part)
        credential_number = self.cleaned_data['credential_number']
        instance.credential_number = credential_number
        instance.status = 'pending'
        
        if commit:
            instance.save()
        return instance


class BulkImportForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
        help_text="Upload a CSV file with facility data"
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise ValidationError('Please upload a CSV file.')
        
        # Enhanced CSV validation with flexible credential number handling
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Get the headers from CSV
            headers = csv_reader.fieldnames
            if not headers:
                raise ValidationError('CSV file appears to be empty or has no headers.')
            
            # Clean headers (remove quotes, extra spaces)
            cleaned_headers = [header.strip().strip('"\'') for header in headers if header]
            
            # Required columns with flexible matching
            required_columns = {
                'name': ['name', 'facility name', 'facilityname'],
                'type': ['type', 'facility type', 'facilitytype', 'category'],
                'credential_number': [
                    'credential number', 'credentialnumber', 'credential', 
                    'registration number', 'registrationnumber', 'registration',
                    'inspection number', 'inspectionnumber', 'number', 'id'
                ],
                'address': ['address', 'location', 'street'],
                'state': ['state', 'province'],
                'county': ['county', 'district', 'region'],
                'bed_count': ['bed count', 'bedcount', 'beds', 'capacity']
            }
            
            # Check if required columns exist with flexible matching
            missing_columns = []
            found_mappings = {}
            
            for req_key, possible_names in required_columns.items():
                found = False
                for header in cleaned_headers:
                    header_normalized = header.lower().replace(' ', '').replace('_', '').replace('-', '')
                    for possible_name in possible_names:
                        possible_normalized = possible_name.lower().replace(' ', '').replace('_', '').replace('-', '')
                        if header_normalized == possible_normalized:
                            found_mappings[req_key] = header
                            found = True
                            break
                    if found:
                        break
                
                if not found:
                    missing_columns.append(possible_names[0].title())
            
            if missing_columns:
                raise ValidationError(f'Missing required columns: {", ".join(missing_columns)}. Found columns: {", ".join(cleaned_headers)}')
            
            # Test read a few rows and validate credential numbers
            rows = list(csv_reader)
            if len(rows) == 0:
                raise ValidationError('CSV file contains no data rows.')
            
            # Validate some credential numbers from the CSV
            credential_column = found_mappings['credential_number']
            invalid_credentials = []
            
            for i, row in enumerate(rows[:5]):  # Check first 5 rows
                credential_value = row.get(credential_column, '').strip()
                if credential_value:
                    normalized = Facility.normalize_credential_input(credential_value)
                    if not Facility.is_valid_credential_format(normalized):
                        invalid_credentials.append(f"Row {i+2}: '{credential_value}'")
            
            if invalid_credentials:
                raise ValidationError(f'Invalid credential number format in: {", ".join(invalid_credentials)}. Expected: 2-5 digits or XXXXX-AGC-X format.')
                
        except UnicodeDecodeError:
            raise ValidationError('Cannot read CSV file. Please ensure it is saved in UTF-8 format.')
        except Exception as e:
            if isinstance(e, ValidationError):
                raise e
            raise ValidationError(f'Invalid CSV file: {str(e)}')
        
        file.seek(0)  # Reset file pointer
        return file


class ApprovalForm(forms.Form):
    action = forms.ChoiceField(choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ], widget=forms.Select(attrs={'class': 'form-select'}))
    
    admin_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text="Add notes about your decision"
    )
    
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=False,
        help_text="Required if rejecting"
    )
    
    def __init__(self, *args, **kwargs):
        self.facility = kwargs.pop('facility', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        rejection_reason = cleaned_data.get('rejection_reason')
        
        if action == 'reject' and not rejection_reason:
            raise ValidationError('Rejection reason is required when rejecting a facility.')
        
        return cleaned_data


class FacilityFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + [
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('pending', 'Pending Approval'),
            ('rejected', 'Rejected'),
            ('draft', 'Draft')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    facility_type = forms.ChoiceField(
        choices=[('', 'All Types')] + [
            ('ALZHEIMER DISEASE', 'Alzheimer Disease'),
            ('ASSISTED LIVING SERVICES', 'Assisted Living Services'),
            ('INDIVIDUALS WITH INTELLECTUAL DISABILITES', 'Intellectual Disabilities'),
            ('MENTAL ILLNESS', 'Mental Illness'),
            ('RESIDENTIAL FACILITY FOR ELDERLY OR DISABLED PERSONS', 'Elderly/Disabled Care'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    state = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Filter by state'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search facilities...'})
    )
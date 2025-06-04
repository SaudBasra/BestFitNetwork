# facility_admin/forms.py
from django import forms
from search.models import Facility
from django.core.exceptions import ValidationError
import csv
import io

class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = [
            'name', 'facility_type', 'endorsement', 'inspection_number',
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
            'inspection_number': forms.TextInput(attrs={'class': 'form-control'}),
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

    def clean_inspection_number(self):
        inspection_number = self.cleaned_data['inspection_number']
        # Check for duplicates
        existing = Facility.objects.filter(inspection_number=inspection_number)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise ValidationError('A facility with this inspection number already exists.')
        return inspection_number


class PublicRegistrationForm(forms.ModelForm):
    submitter_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    submitter_email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    submitter_phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    submission_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text="Any additional information about your facility"
    )

    class Meta:
        model = Facility
        fields = [
            'name', 'facility_type', 'endorsement', 'inspection_number',
            'address', 'state', 'county', 'contact', 'contact_person',
            'bed_count', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'facility_type': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('ALZHEIMER DISEASE', 'Alzheimer Disease'),
                ('ASSISTED LIVING SERVICES', 'Assisted Living Services'),
                ('INDIVIDUALS WITH INTELLECTUAL DISABILITES', 'Intellectual Disabilities'),
                ('MENTAL ILLNESS', 'Mental Illness'),
                ('RESIDENTIAL FACILITY FOR ELDERLY OR DISABLED PERSONS', 'Elderly/Disabled Care'),
            ]),
            'endorsement': forms.TextInput(attrs={'class': 'form-control'}),
            'inspection_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'county': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'bed_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class BulkImportForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
        help_text="Upload a CSV file with facility data"
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise ValidationError('Please upload a CSV file.')
        
        # Basic CSV validation
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            rows = list(csv_reader)
            
            # Check if required columns exist
            required_columns = ['Name', 'Type', 'Inspection Number', 'Address', 'State', 'County', 'Bed Count']
            first_row = rows[0] if rows else {}
            missing_columns = [col for col in required_columns if col not in first_row.keys()]
            
            if missing_columns:
                raise ValidationError(f'Missing required columns: {", ".join(missing_columns)}')
                
        except Exception as e:
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
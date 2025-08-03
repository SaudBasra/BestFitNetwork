import re

def validate_credential_format(credential):
    """Validate full credential number format"""
    pattern = r'^\d{4,5}-AGC-\d+$'
    return re.match(pattern, credential) is not None

def extract_registration_number(credential):
    """Extract registration number from credential"""
    if credential and '-AGC' in credential:
        return credential.split('-AGC')[0]
    return credential

def find_facility_by_registration(registration_number):
    """Find facility by registration number (first 4-5 digits)"""
    from search.models import Facility
    return Facility.objects.filter(
        credential_number__startswith=f"{registration_number}-AGC"
    ).first()

def construct_credential_number(registration_number, suffix):
    """Construct full credential number"""
    return f"{registration_number}-AGC-{suffix}"
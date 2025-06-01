import os
import sys
import django
import pandas as pd

# Add project root (where manage.py lives) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BestFitNetwork.settings")  # Adjust if your settings module is named differently
django.setup()

# Now import your model
from search.models import Facility

def import_facility_data():
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bestfit.xlsx")
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File '{file_path}' not found!")
        return

    df = pd.read_excel(file_path, dtype=str)
    df.columns = df.columns.str.strip()
    print("Excel Columns Found:", df.columns.tolist())

    for _, row in df.iterrows():
        obj, created = Facility.objects.get_or_create(
            inspection_number=row["Inspection Number"],
            defaults={
                "name": row["Name"],
                "facility_type": row["Type"],
                "endorsement": row["Endorsement"],
                "address": row["Address"],
                "state": row["State"],
                "county": row["County"],
                "contact": row["Contact"],
                "contact_person": row["Contact Person"],
                "bed_count": row["Bed Count"]
            }
        )
        if created:
            print(f"✅ Added: {row['Name']}")
        else:
            print(f"⚠️ Skipped Duplicate: {row['Name']} (Inspection Number: {row['Inspection Number']})")

    print("✅ Data Import Completed!")

# Run function
import_facility_data()

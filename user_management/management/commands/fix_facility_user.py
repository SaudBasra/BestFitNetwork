# user_management/management/commands/fix_facility_user.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from search.models import Facility
from user_management.models import UserProfile

class Command(BaseCommand):
    help = 'Fix existing facility user profile'
    
    def add_arguments(self, parser):
        parser.add_argument('inspection_number', type=str, help='Facility inspection number')
    
    def handle(self, *args, **options):
        inspection_number = options['inspection_number']
        
        self.stdout.write(f"🔧 Fixing facility user for inspection number: {inspection_number}")
        
        try:
            # Get the facility
            facility = Facility.objects.get(inspection_number=inspection_number)
            self.stdout.write(f"✅ Found facility: {facility.name}")
            
            # Get the user
            user = User.objects.get(username=inspection_number)
            self.stdout.write(f"✅ Found user: {user.username}")
            
            # Get or create profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            if created:
                self.stdout.write("✅ Created new profile")
            else:
                self.stdout.write("✅ Found existing profile")
            
            # Fix the profile
            self.stdout.write("🔧 Updating profile...")
            profile.user_type = 'facility_staff'
            profile.facility = facility
            profile.position = 'Facility Staff'
            profile.is_verified = True
            profile.save()
            
            # Verify the fix
            profile.refresh_from_db()
            self.stdout.write(f"✅ Profile fixed:")
            self.stdout.write(f"   Type: {profile.user_type}")
            self.stdout.write(f"   Facility: {profile.facility.name}")
            
            self.stdout.write(self.style.SUCCESS("🎉 User profile fixed successfully!"))
            
        except Facility.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Facility not found: {inspection_number}"))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User not found: {inspection_number}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from search.models import Facility

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup facility staff users for existing facilities (optional command)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            type=str,
            default='bestfit#123',
            help='Password for facility staff accounts'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate existing users'
        )
        
    def handle(self, *args, **options):
        password = options['password']
        force = options['force']
        
        facilities = Facility.objects.filter(
            status='active',
            contact_person__isnull=False
        ).exclude(contact_person='')
        
        created_count = 0
        skipped_count = 0
        
        for facility in facilities:
            username = f"facility_{facility.inspection_number}"
            
            if User.objects.filter(username=username).exists() and not force:
                skipped_count += 1
                self.stdout.write(f'⏭️  User exists for: {facility.name}')
                continue
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': facility.contact_person.split()[0] if facility.contact_person else 'Facility',
                    'last_name': ' '.join(facility.contact_person.split()[1:]) if len(facility.contact_person.split()) > 1 else 'Staff',
                    'email': f"{facility.inspection_number}@facility.bestfit.local",
                    'user_type': 'facility_staff',
                    'facility': facility,
                    'is_staff': False,
                    'is_active': True,
                }
            )
            
            if created or force:
                user.set_password(password)
                user.save()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created user for: {facility.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Summary: {created_count} created, {skipped_count} skipped')
        )
        self.stdout.write(
            self.style.WARNING(f'💡 Facility staff can login with inspection number + contact person name + password "{password}"')
        )
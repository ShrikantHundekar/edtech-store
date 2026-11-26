from django.core.management.base import BaseCommand
from apps.accounts.models import CustomUser


class Command(BaseCommand):
    help = "Seed demo accounts (student@edtech.com and admin@edtech.com) for development and evaluation."

    def handle(self, *args, **options):
        # Student Demo Account
        student, created = CustomUser.objects.get_or_create(
            email='student@edtech.com',
            defaults={
                'role': CustomUser.ROLE_STUDENT,
                'full_name': 'Demo Student',
                'is_active': True,
            }
        )
        student.set_password('StudentPass@123')
        student.role = CustomUser.ROLE_STUDENT
        student.is_active = True
        student.save()
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} student demo: student@edtech.com"))

        # Admin Demo Account
        admin, created = CustomUser.objects.get_or_create(
            email='admin@edtech.com',
            defaults={
                'role': CustomUser.ROLE_ADMIN,
                'full_name': 'Demo Admin',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin.set_password('AdminPass@123')
        admin.role = CustomUser.ROLE_ADMIN
        admin.is_active = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} admin demo: admin@edtech.com"))

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

User = get_user_model()


class CustomUserModelTests(TestCase):
    def test_create_student_user(self):
        user = User.objects.create_user(
            email="student@example.com",
            password="StrongPassword123!",
            full_name="Aarav Sharma",
            phone_number="+919876543210"
        )
        self.assertEqual(user.email, "student@example.com")
        self.assertEqual(user.full_name, "Aarav Sharma")
        self.assertEqual(user.phone_number, "+919876543210")
        self.assertEqual(user.role, User.ROLE_STUDENT)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_admin)
        self.assertTrue(user.check_password("StrongPassword123!"))
        self.assertEqual(str(user), "Aarav Sharma <student@example.com> (STUDENT)")

    def test_argon2_password_hashing(self):
        user = User.objects.create_user(
            email="argon2user@example.com",
            password="MySecretPassword999!",
            full_name="Argon2 Tester"
        )
        # Verify hash algorithm identifier in password field starts with 'argon2'
        self.assertTrue(user.password.startswith("argon2"))
        self.assertIn("argon2id", user.password)
        # Verify authentication verification
        self.assertTrue(user.check_password("MySecretPassword999!"))
        self.assertFalse(user.check_password("WrongPassword!"))

    def test_create_admin_superuser(self):
        admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPassword123!",
            full_name="System Administrator"
        )
        self.assertEqual(admin_user.email, "admin@example.com")
        self.assertEqual(admin_user.role, User.ROLE_ADMIN)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_admin)
        self.assertFalse(admin_user.is_student)

    def test_email_uniqueness_and_normalization(self):
        User.objects.create_user(
            email="TestUser@Example.COM",
            password="Password123!",
            full_name="Test User 1"
        )
        # Normalization lowercases the domain
        saved_user = User.objects.get(email="TestUser@example.com")
        self.assertEqual(saved_user.email, "TestUser@example.com")

        # Duplicate email raises IntegrityError
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="TestUser@example.com",
                password="AnotherPassword123!",
                full_name="Test User 2"
            )

    def test_missing_email_raises_value_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="",
                password="Password123!",
                full_name="No Email User"
            )

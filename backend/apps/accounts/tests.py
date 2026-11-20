from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

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


class AuthAPITests(APITestCase):
    def setUp(self):
        self.register_url = reverse('auth_register')
        self.login_url = reverse('auth_login')
        self.refresh_url = reverse('auth_refresh')
        self.logout_url = reverse('auth_logout')
        self.me_url = reverse('auth_me')

        self.test_user = User.objects.create_user(
            email="existingstudent@example.com",
            password="SecurePassword123!",
            full_name="Existing Student"
        )

    def test_student_registration_success(self):
        payload = {
            "email": "newstudent@example.com",
            "password": "StrongPassword2026!",
            "confirm_password": "StrongPassword2026!",
            "full_name": "Rohan Deshmukh",
            "phone_number": "+919988776655"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], "newstudent@example.com")
        self.assertEqual(response.data['user']['role'], "STUDENT")
        self.assertTrue(response.data['user']['is_student'])

    def test_registration_duplicate_email(self):
        payload = {
            "email": "existingstudent@example.com",
            "password": "StrongPassword2026!",
            "full_name": "Duplicate Tester"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_registration_weak_password(self):
        payload = {
            "email": "weakpass@example.com",
            "password": "123",
            "full_name": "Weak Pass User"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_password_mismatch(self):
        payload = {
            "email": "mismatch@example.com",
            "password": "ValidPassword123!",
            "confirm_password": "DifferentPassword123!",
            "full_name": "Mismatch Tester"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirm_password', response.data)

    def test_student_login_success(self):
        payload = {
            "email": "existingstudent@example.com",
            "password": "SecurePassword123!"
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], "existingstudent@example.com")
        self.assertEqual(response.data['user']['role'], "STUDENT")

    def test_login_invalid_password(self):
        payload = {
            "email": "existingstudent@example.com",
            "password": "WrongPassword999!"
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_login_nonexistent_email(self):
        payload = {
            "email": "notfound@example.com",
            "password": "SomePassword123!"
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_token_refresh_lifecycle(self):
        # 1. Login to obtain refresh token
        login_resp = self.client.post(self.login_url, {
            "email": "existingstudent@example.com",
            "password": "SecurePassword123!"
        }, format='json')
        refresh_token = login_resp.data['tokens']['refresh']

        # 2. Refresh access token
        refresh_resp = self.client.post(self.refresh_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_resp.data)

        # 3. Invalid refresh token returns 401
        invalid_resp = self.client.post(self.refresh_url, {"refresh": "invalid.fake.token"}, format='json')
        self.assertEqual(invalid_resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_token(self):
        # 1. Login
        login_resp = self.client.post(self.login_url, {
            "email": "existingstudent@example.com",
            "password": "SecurePassword123!"
        }, format='json')
        access_token = login_resp.data['tokens']['access']
        refresh_token = login_resp.data['tokens']['refresh']

        # 2. Logout with authenticated client
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_resp = self.client.post(self.logout_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(logout_resp.status_code, status.HTTP_200_OK)

        # 3. Attempting to refresh using the blacklisted refresh token MUST fail
        retry_refresh = self.client.post(self.refresh_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(retry_refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_me_endpoint(self):
        # Unauthenticated request -> 401
        self.client.credentials()
        unauth_resp = self.client.get(self.me_url)
        self.assertEqual(unauth_resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated request -> 200 with profile
        refresh = RefreshToken.for_user(self.test_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        auth_resp = self.client.get(self.me_url)
        self.assertEqual(auth_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(auth_resp.data['email'], "existingstudent@example.com")
        self.assertEqual(auth_resp.data['full_name'], "Existing Student")
        self.assertEqual(auth_resp.data['role'], "STUDENT")

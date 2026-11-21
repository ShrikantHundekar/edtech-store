import os
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.catalog.models import Board, ClassLevel, Subject, Chapter, Material
from apps.products.models import Product, Price
from apps.entitlements.models import Entitlement, ManualAccessLog
from apps.entitlements.services import (
    has_access_to_chapter,
    has_access_to_material,
    calculate_pass_validity_window,
    provision_class_pass_entitlement,
)

User = get_user_model()


class TimeBoundPassValidityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pass_student@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)

        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.class_10 = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.class_12 = ClassLevel.objects.create(board=self.board, name="Class 12", slug="class-12")

        # Class 10 Subjects & Chapters
        self.math_10 = Subject.objects.create(academic_class=self.class_10, name="Mathematics", slug="math-10")
        self.sci_10 = Subject.objects.create(academic_class=self.class_10, name="Science", slug="sci-10")

        self.ch_math_10 = Chapter.objects.create(subject=self.math_10, chapter_number=1, title="Real Numbers", slug="real-numbers")
        self.ch_sci_10 = Chapter.objects.create(subject=self.sci_10, chapter_number=1, title="Chemical Reactions", slug="chem-react")

        # Class 12 Subject & Chapter (unrelated class)
        self.phy_12 = Subject.objects.create(academic_class=self.class_12, name="Physics", slug="phy-12")
        self.ch_phy_12 = Chapter.objects.create(subject=self.phy_12, chapter_number=1, title="Electrostatics", slug="electrostatics")

        # Materials
        protected_root = getattr(settings, 'PROTECTED_MEDIA_ROOT', settings.BASE_DIR / 'protected_media')
        mat_dir = os.path.join(protected_root, 'materials')
        os.makedirs(mat_dir, exist_ok=True)

        self.test_pdf = os.path.join(mat_dir, 'pass_test_note.pdf')
        with open(self.test_pdf, 'wb') as f:
            f.write(b"%PDF-1.4 Class Pass Test Note Content")

        self.mat_math_10 = Material.objects.create(
            chapter=self.ch_math_10,
            title="Class 10 Math Notes",
            file_path="materials/pass_test_note.pdf",
            file_size_bytes=35,
            mime_type="application/pdf"
        )
        self.mat_sci_10 = Material.objects.create(
            chapter=self.ch_sci_10,
            title="Class 10 Science Notes",
            file_path="materials/pass_test_note.pdf",
            file_size_bytes=35,
            mime_type="application/pdf"
        )
        self.mat_phy_12 = Material.objects.create(
            chapter=self.ch_phy_12,
            title="Class 12 Physics Notes",
            file_path="materials/pass_test_note.pdf",
            file_size_bytes=35,
            mime_type="application/pdf"
        )

        # Products
        self.monthly_pass = Product.objects.create(
            title="Class 10 Monthly Pass",
            slug="p-c10-monthly",
            product_type=Product.PRODUCT_TYPE_MONTHLY_PASS,
            academic_class=self.class_10,
            board=self.board
        )
        Price.objects.create(product=self.monthly_pass, amount_paise=29900, is_current=True)

        self.annual_pass = Product.objects.create(
            title="Class 10 Annual Pass",
            slug="p-c10-annual",
            product_type=Product.PRODUCT_TYPE_ANNUAL_PASS,
            academic_class=self.class_10,
            board=self.board
        )
        Price.objects.create(product=self.annual_pass, amount_paise=249900, is_current=True)

    def tearDown(self):
        if os.path.exists(self.test_pdf):
            try:
                os.remove(self.test_pdf)
            except OSError:
                pass

    def test_monthly_pass_duration_is_30_days(self):
        self.assertEqual(self.monthly_pass.pass_duration_days, 30)
        self.assertEqual(self.monthly_pass.access_duration, "30 Days")

        before = timezone.now()
        window = calculate_pass_validity_window(self.user, self.class_10.id, duration_days=30)
        after = timezone.now()

        self.assertFalse(window["is_renewal"])
        self.assertEqual(window["duration_days"], 30)
        # Expected duration is exactly 30 days
        diff = window["valid_until"] - window["valid_from"]
        self.assertEqual(diff.days, 30)
        self.assertTrue(before <= window["valid_from"] <= after)

    def test_annual_pass_duration_is_365_days(self):
        self.assertEqual(self.annual_pass.pass_duration_days, 365)
        self.assertEqual(self.annual_pass.access_duration, "365 Days")

        window = calculate_pass_validity_window(self.user, self.class_10.id, duration_days=365)
        self.assertFalse(window["is_renewal"])
        self.assertEqual(window["duration_days"], 365)
        diff = window["valid_until"] - window["valid_from"]
        self.assertEqual(diff.days, 365)

    def test_product_api_returns_pass_duration_days(self):
        # Monthly pass detail
        resp_m = self.client.get(f'/api/v1/products/{self.monthly_pass.id}/')
        self.assertEqual(resp_m.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_m.data['pass_duration_days'], 30)
        self.assertEqual(resp_m.data['access_duration'], "30 Days")

        # Annual pass detail
        resp_a = self.client.get(f'/api/v1/products/{self.annual_pass.id}/')
        self.assertEqual(resp_a.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_a.data['pass_duration_days'], 365)
        self.assertEqual(resp_a.data['access_duration'], "365 Days")

    def test_active_pass_unlocks_all_subjects_and_chapters_in_class(self):
        # Before pass: student has no access
        self.assertFalse(has_access_to_chapter(self.user, self.ch_math_10))
        self.assertFalse(has_access_to_chapter(self.user, self.ch_sci_10))

        # Provision 30-day class pass
        entitlement = provision_class_pass_entitlement(self.user, self.class_10.id, duration_days=30)
        self.assertEqual(entitlement.product_type, 'CLASS_PASS')
        self.assertEqual(entitlement.access_type, 'TIME_BOUND')
        self.assertTrue(entitlement.is_currently_active)

        # Student now has full access to ALL subjects and chapters in Class 10
        self.assertTrue(has_access_to_chapter(self.user, self.ch_math_10))
        self.assertTrue(has_access_to_chapter(self.user, self.ch_sci_10))
        self.assertTrue(has_access_to_material(self.user, self.mat_math_10))
        self.assertTrue(has_access_to_material(self.user, self.mat_sci_10))

        # Can stream Class 10 materials via endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp_math = self.client.get(f'/api/v1/materials/{self.mat_math_10.id}/stream/')
        self.assertEqual(resp_math.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_math['Content-Type'], 'application/pdf')

        resp_sci = self.client.get(f'/api/v1/materials/{self.mat_sci_10.id}/stream/')
        self.assertEqual(resp_sci.status_code, status.HTTP_200_OK)

        # But does NOT unlock chapters or materials in Class 12
        self.assertFalse(has_access_to_chapter(self.user, self.ch_phy_12))
        self.assertFalse(has_access_to_material(self.user, self.mat_phy_12))
        resp_phy = self.client.get(f'/api/v1/materials/{self.mat_phy_12.id}/stream/')
        self.assertEqual(resp_phy.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_pass_immediately_denies_access(self):
        # Create an expired Class Pass (expired 1 day ago)
        Entitlement.objects.create(
            user=self.user,
            product_type='CLASS_PASS',
            scope_id=self.class_10.id,
            access_type='TIME_BOUND',
            valid_from=timezone.now() - timedelta(days=31),
            valid_until=timezone.now() - timedelta(days=1),
            status='ACTIVE'
        )

        # Verification: access denied
        self.assertFalse(has_access_to_chapter(self.user, self.ch_math_10))
        self.assertFalse(has_access_to_material(self.user, self.mat_math_10))

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp = self.client.get(f'/api/v1/materials/{self.mat_math_10.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_early_pass_renewal_stacks_from_existing_expiry_date(self):
        # 1. Existing active pass expiring in 15 days
        existing_expiry = timezone.now() + timedelta(days=15)
        Entitlement.objects.create(
            user=self.user,
            product_type='CLASS_PASS',
            scope_id=self.class_10.id,
            access_type='TIME_BOUND',
            valid_from=timezone.now() - timedelta(days=15),
            valid_until=existing_expiry,
            status='ACTIVE'
        )

        # 2. Preview 30-day renewal
        window = calculate_pass_validity_window(self.user, self.class_10.id, duration_days=30)
        self.assertTrue(window["is_renewal"])
        self.assertEqual(window["base_time"], existing_expiry)
        # new_valid_until = existing_valid_until + 30 days
        self.assertEqual(window["valid_until"], existing_expiry + timedelta(days=30))
        self.assertEqual(window["remaining_active_days"], 15)

        # 3. Provision renewal
        renewal_ent = provision_class_pass_entitlement(self.user, self.class_10.id, duration_days=30)
        self.assertEqual(renewal_ent.valid_until, existing_expiry + timedelta(days=30))
        # Total days of access is now 45 days (15 remaining + 30 new)
        total_days = round((renewal_ent.valid_until - timezone.now()).total_seconds() / 86400)
        self.assertEqual(total_days, 45)

    def test_multiple_consecutive_pass_renewals_stack(self):
        # First purchase (30 days)
        pass1 = provision_class_pass_entitlement(self.user, self.class_10.id, duration_days=30)
        self.assertEqual(round((pass1.valid_until - timezone.now()).total_seconds() / 86400), 30)

        # Second purchase (another 30 days stacked on top of first)
        pass2 = provision_class_pass_entitlement(self.user, self.class_10.id, duration_days=30)
        self.assertEqual(pass2.valid_until, pass1.valid_until + timedelta(days=30))
        self.assertEqual(round((pass2.valid_until - timezone.now()).total_seconds() / 86400), 60)

        # Third purchase (Annual 365 days stacked on top of second)
        pass3 = provision_class_pass_entitlement(self.user, self.class_10.id, duration_days=365)
        self.assertEqual(pass3.valid_until, pass2.valid_until + timedelta(days=365))
        self.assertEqual(round((pass3.valid_until - timezone.now()).total_seconds() / 86400), 425)

    def test_expired_pass_does_not_stack_from_past(self):
        # Pass expired 10 days ago
        Entitlement.objects.create(
            user=self.user,
            product_type='CLASS_PASS',
            scope_id=self.class_10.id,
            access_type='TIME_BOUND',
            valid_from=timezone.now() - timedelta(days=40),
            valid_until=timezone.now() - timedelta(days=10),
            status='ACTIVE'
        )

        # New purchase should start from NOW, not from 10 days ago
        window = calculate_pass_validity_window(self.user, self.class_10.id, duration_days=30)
        self.assertFalse(window["is_renewal"])
        days_from_now = round((window["valid_until"] - timezone.now()).total_seconds() / 86400)
        self.assertEqual(days_from_now, 30)

    def test_api_renewal_preview(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create active pass with 10 days left
        existing_expiry = timezone.now() + timedelta(days=10)
        Entitlement.objects.create(
            user=self.user,
            product_type='CLASS_PASS',
            scope_id=self.class_10.id,
            access_type='TIME_BOUND',
            valid_from=timezone.now() - timedelta(days=20),
            valid_until=existing_expiry,
            status='ACTIVE'
        )

        # Check ownership endpoint
        resp_own = self.client.get(f'/api/v1/products/{self.monthly_pass.id}/ownership/')
        self.assertEqual(resp_own.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_own.data['can_purchase'])
        self.assertTrue(resp_own.data['renewal_preview']['is_renewal'])
        self.assertEqual(resp_own.data['renewal_preview']['remaining_active_days'], 10)

        # Check calculate-price endpoint
        resp_calc = self.client.get(f'/api/v1/products/{self.monthly_pass.id}/calculate-price/')
        self.assertEqual(resp_calc.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_calc.data['renewal_preview']['is_renewal'])


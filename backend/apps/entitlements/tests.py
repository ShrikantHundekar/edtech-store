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


class EntitlementModelAndStateManagementTests(TestCase):
    """
    Issue #35: Entitlements database model and state management:
    - User content licenses decoupled from orders.
    - Schema Fields: user_id, product_type (CHAPTER, SUBJECT, CLASS_PASS, BUNDLE),
      scope_id, access_type (LIFETIME, TIME_BOUND), valid_from, valid_until,
      status (ACTIVE, EXPIRED, REVOKED).
    - Direct entitlement queries used for fast, indexed authorization checks.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            email="entitlement_model_test@example.com",
            password="StrongPassword123!",
            role="STUDENT"
        )

    def test_lifetime_access_entitlement_state(self):
        """Lifetime access has no expiration and is currently active."""
        entitlement = Entitlement.objects.create(
            user=self.user,
            product_type='CHAPTER',
            scope_id=101,
            access_type='LIFETIME',
            status='ACTIVE'
        )
        self.assertEqual(entitlement.access_type, 'LIFETIME')
        self.assertIsNone(entitlement.valid_until)
        self.assertTrue(entitlement.is_currently_active)

    def test_time_bound_access_active_vs_expired(self):
        """Time-bound access is active before expiration and inactive after expiration."""
        now = timezone.now()
        active_entitlement = Entitlement.objects.create(
            user=self.user,
            product_type='CLASS_PASS',
            scope_id=10,
            access_type='TIME_BOUND',
            valid_from=now - timedelta(days=1),
            valid_until=now + timedelta(days=29),
            status='ACTIVE'
        )
        self.assertTrue(active_entitlement.is_currently_active)

        expired_entitlement = Entitlement.objects.create(
            user=self.user,
            product_type='CLASS_PASS',
            scope_id=12,
            access_type='TIME_BOUND',
            valid_from=now - timedelta(days=40),
            valid_until=now - timedelta(days=10),
            status='ACTIVE'
        )
        self.assertFalse(expired_entitlement.is_currently_active)

    def test_revoked_status_state(self):
        """Revoked entitlement returns False for is_currently_active regardless of access_type."""
        entitlement = Entitlement.objects.create(
            user=self.user,
            product_type='SUBJECT',
            scope_id=202,
            access_type='LIFETIME',
            status='REVOKED'
        )
        self.assertEqual(entitlement.status, 'REVOKED')
        self.assertFalse(entitlement.is_currently_active)

    def test_direct_entitlement_queryset_authorization(self):
        """Direct queries using active(), for_user(), and is_entitled() for fast authorization."""
        Entitlement.objects.create(
            user=self.user,
            product_type='CHAPTER',
            scope_id=301,
            access_type='LIFETIME',
            status='ACTIVE'
        )
        Entitlement.objects.create(
            user=self.user,
            product_type='SUBJECT',
            scope_id=401,
            access_type='LIFETIME',
            status='REVOKED'
        )

        # Direct authorization check via custom manager
        self.assertTrue(Entitlement.objects.is_entitled(self.user, 'CHAPTER', 301))
        self.assertFalse(Entitlement.objects.is_entitled(self.user, 'SUBJECT', 401))
        self.assertFalse(Entitlement.objects.is_entitled(self.user, 'CHAPTER', 999))

        active_count = Entitlement.objects.for_user(self.user).active().count()
        self.assertEqual(active_count, 1)

    def test_entitlement_decoupled_from_order(self):
        """Entitlement can be created without an order (e.g. manual administrative grant)."""
        entitlement = Entitlement.objects.create(
            user=self.user,
            product_type='BUNDLE',
            scope_id=501,
            access_type='LIFETIME',
            order=None,
            status='ACTIVE'
        )
        self.assertIsNone(entitlement.order)
        self.assertTrue(entitlement.is_currently_active)


class AtomicOrderFulfillmentEntitlementTests(TestCase):
    """
    Issue #36: Atomic order fulfillment service provisioning entitlements.
    Acceptance Criteria:
    - [x] Provisions Lifetime access for Chapter Notes, Subject Packs, and Bundles.
    - [x] Provisions Time-Bound access for Monthly and Annual passes.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            email="fulfill_student@example.com",
            password="StrongPassword123!",
            role="STUDENT"
        )
        self.board = Board.objects.create(name="CBSE FulFill", slug="cbse-fulfill")
        self.cls = ClassLevel.objects.create(board=self.board, name="Class 10", slug="c10-fulfill")
        self.subject = Subject.objects.create(academic_class=self.cls, name="Biology", slug="bio-fulfill")
        self.chapter = Chapter.objects.create(subject=self.subject, chapter_number=1, title="Life Processes", slug="life-proc")

        # Products
        self.prod_ch = Product.objects.create(
            title="Life Processes Notes",
            slug="life-proc-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.chapter,
            is_active=True
        )
        self.prod_sub = Product.objects.create(
            title="Class 10 Biology Pack",
            slug="c10-bio-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.subject,
            is_active=True
        )
        self.prod_monthly = Product.objects.create(
            title="Class 10 Monthly Pass",
            slug="c10-monthly-pass",
            product_type=Product.PRODUCT_TYPE_MONTHLY_PASS,
            academic_class=self.cls,
            board=self.board,
            is_active=True
        )
        self.prod_annual = Product.objects.create(
            title="Class 10 Annual Pass",
            slug="c10-annual-pass",
            product_type=Product.PRODUCT_TYPE_ANNUAL_PASS,
            academic_class=self.cls,
            board=self.board,
            is_active=True
        )
        self.prod_bundle = Product.objects.create(
            title="Class 10 Science Combo",
            slug="c10-science-combo",
            product_type=Product.PRODUCT_TYPE_BUNDLE,
            is_active=True
        )
        self.prod_bundle.bundle_items.create(target_type='SUBJECT', subject=self.subject)
        self.prod_bundle.bundle_items.create(target_type='CHAPTER', chapter=self.chapter)

    def test_provisions_lifetime_access_for_chapter_notes(self):
        from apps.orders.models import Order, OrderItem
        from apps.entitlements.services import provision_order_entitlements

        order = Order.objects.create(
            user=self.user,
            order_number=Order.generate_order_number(),
            status=Order.STATUS_PAID,
            gross_amount_paise=4900,
            net_payable_paise=4900
        )
        OrderItem.objects.create(order=order, product=self.prod_ch, unit_price_paise=4900, net_price_paise=4900)

        entitlements = provision_order_entitlements(order)
        self.assertEqual(len(entitlements), 1)
        ent = entitlements[0]
        self.assertEqual(ent.product_type, 'CHAPTER')
        self.assertEqual(ent.scope_id, self.chapter.id)
        self.assertEqual(ent.access_type, 'LIFETIME')
        self.assertIsNone(ent.valid_until)
        self.assertEqual(ent.status, 'ACTIVE')

    def test_provisions_lifetime_access_for_subject_pack(self):
        from apps.orders.models import Order, OrderItem
        from apps.entitlements.services import provision_order_entitlements

        order = Order.objects.create(
            user=self.user,
            order_number=Order.generate_order_number(),
            status=Order.STATUS_PAID,
            gross_amount_paise=19900,
            net_payable_paise=19900
        )
        OrderItem.objects.create(order=order, product=self.prod_sub, unit_price_paise=19900, net_price_paise=19900)

        entitlements = provision_order_entitlements(order)
        self.assertEqual(len(entitlements), 1)
        ent = entitlements[0]
        self.assertEqual(ent.product_type, 'SUBJECT')
        self.assertEqual(ent.scope_id, self.subject.id)
        self.assertEqual(ent.access_type, 'LIFETIME')
        self.assertIsNone(ent.valid_until)
        self.assertEqual(ent.status, 'ACTIVE')

    def test_provisions_lifetime_access_for_bundle(self):
        from apps.orders.models import Order, OrderItem
        from apps.entitlements.services import provision_order_entitlements

        order = Order.objects.create(
            user=self.user,
            order_number=Order.generate_order_number(),
            status=Order.STATUS_PAID,
            gross_amount_paise=29900,
            net_payable_paise=29900
        )
        OrderItem.objects.create(order=order, product=self.prod_bundle, unit_price_paise=29900, net_price_paise=29900)

        entitlements = provision_order_entitlements(order)
        # Bundle itself + 1 subject + 1 chapter = 3 entitlements
        self.assertEqual(len(entitlements), 3)
        bundle_ent = next(e for e in entitlements if e.product_type == 'BUNDLE')
        self.assertEqual(bundle_ent.access_type, 'LIFETIME')
        self.assertEqual(bundle_ent.status, 'ACTIVE')

        sub_ent = next(e for e in entitlements if e.product_type == 'SUBJECT')
        self.assertEqual(sub_ent.scope_id, self.subject.id)
        self.assertEqual(sub_ent.access_type, 'LIFETIME')

        ch_ent = next(e for e in entitlements if e.product_type == 'CHAPTER')
        self.assertEqual(ch_ent.scope_id, self.chapter.id)
        self.assertEqual(ch_ent.access_type, 'LIFETIME')

    def test_provisions_time_bound_access_for_monthly_pass(self):
        from apps.orders.models import Order, OrderItem
        from apps.entitlements.services import provision_order_entitlements

        order = Order.objects.create(
            user=self.user,
            order_number=Order.generate_order_number(),
            status=Order.STATUS_PAID,
            gross_amount_paise=29900,
            net_payable_paise=29900
        )
        OrderItem.objects.create(order=order, product=self.prod_monthly, unit_price_paise=29900, net_price_paise=29900)

        entitlements = provision_order_entitlements(order)
        self.assertEqual(len(entitlements), 1)
        ent = entitlements[0]
        self.assertEqual(ent.product_type, 'CLASS_PASS')
        self.assertEqual(ent.scope_id, self.cls.id)
        self.assertEqual(ent.access_type, 'TIME_BOUND')
        self.assertIsNotNone(ent.valid_until)
        days = round((ent.valid_until - ent.valid_from).total_seconds() / 86400)
        self.assertEqual(days, 30)
        self.assertTrue(ent.is_currently_active)

    def test_provisions_time_bound_access_for_annual_pass(self):
        from apps.orders.models import Order, OrderItem
        from apps.entitlements.services import provision_order_entitlements

        order = Order.objects.create(
            user=self.user,
            order_number=Order.generate_order_number(),
            status=Order.STATUS_PAID,
            gross_amount_paise=249900,
            net_payable_paise=249900
        )
        OrderItem.objects.create(order=order, product=self.prod_annual, unit_price_paise=249900, net_price_paise=249900)

        entitlements = provision_order_entitlements(order)
        self.assertEqual(len(entitlements), 1)
        ent = entitlements[0]
        self.assertEqual(ent.product_type, 'CLASS_PASS')
        self.assertEqual(ent.scope_id, self.cls.id)
        self.assertEqual(ent.access_type, 'TIME_BOUND')
        self.assertIsNotNone(ent.valid_until)
        days = round((ent.valid_until - ent.valid_from).total_seconds() / 86400)
        self.assertEqual(days, 365)
        self.assertTrue(ent.is_currently_active)


class AdminManualEntitlementAuditTests(APITestCase):
    """
    Issue #37: Admin manual entitlement grant and revoke with audit logging.
    Requirements:
    - Create ManualAccessLog recording admin_id, student_id, action, reason, timestamp.
    Acceptance Criteria:
    - Reason field is strictly mandatory.
    - Updates entitlement status and logs audit entry.
    """
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin_entitlement@example.com",
            password="AdminPassword123!",
            role="ADMIN"
        )
        self.admin_token = str(RefreshToken.for_user(self.admin).access_token)

        self.student = User.objects.create_user(
            email="student_support@example.com",
            password="StudentPassword123!",
            role="STUDENT"
        )
        self.student_token = str(RefreshToken.for_user(self.student).access_token)

        self.board = Board.objects.create(name="CBSE Audit", slug="cbse-audit")
        self.cls = ClassLevel.objects.create(board=self.board, name="Class 10", slug="c10-audit")
        self.subject = Subject.objects.create(academic_class=self.cls, name="Chemistry", slug="chem-audit")
        self.chapter = Chapter.objects.create(subject=self.subject, chapter_number=1, title="Acids & Bases", slug="acids-bases")

    def test_admin_manual_grant_creates_entitlement_and_audit_log(self):
        """Admin grants access with valid reason; creates entitlement and audit entry."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        payload = {
            "student_id": self.student.id,
            "product_type": "CHAPTER",
            "scope_id": self.chapter.id,
            "access_type": "LIFETIME",
            "reason": "Customer support resolution for duplicate payment ticket #1029"
        }
        resp = self.client.post('/api/v1/admin/entitlements/grant/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['message'], "Entitlement granted successfully.")

        # Entitlement verified
        ent = Entitlement.objects.get(user=self.student, product_type='CHAPTER', scope_id=self.chapter.id)
        self.assertEqual(ent.status, 'ACTIVE')
        self.assertEqual(ent.access_type, 'LIFETIME')
        self.assertIsNone(ent.order)

        # Audit log verified
        log = ManualAccessLog.objects.filter(student=self.student, action='GRANT').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin, self.admin)
        self.assertEqual(log.entitlement, ent)
        self.assertEqual(log.reason, "Customer support resolution for duplicate payment ticket #1029")
        self.assertIsNotNone(log.created_at)

    def test_admin_manual_grant_fails_without_reason(self):
        """Acceptance Criteria: Reason field is strictly mandatory."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        # Missing reason
        payload_missing = {
            "student_id": self.student.id,
            "product_type": "CHAPTER",
            "scope_id": self.chapter.id,
        }
        resp = self.client.post('/api/v1/admin/entitlements/grant/', payload_missing, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", resp.data)

        # Empty whitespace reason
        payload_empty = {
            "student_id": self.student.id,
            "product_type": "CHAPTER",
            "scope_id": self.chapter.id,
            "reason": "   "
        }
        resp2 = self.client.post('/api/v1/admin/entitlements/grant/', payload_empty, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", resp2.data)

        # Ensure no entitlement or log was created
        self.assertFalse(Entitlement.objects.filter(user=self.student).exists())
        self.assertFalse(ManualAccessLog.objects.filter(student=self.student).exists())

    def test_admin_manual_revoke_updates_status_and_logs_audit(self):
        """Admin revokes access with valid reason; updates status to REVOKED and logs audit entry."""
        # Setup existing active entitlement
        ent = Entitlement.objects.create(
            user=self.student,
            product_type='SUBJECT',
            scope_id=self.subject.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        payload = {
            "reason": "Student requested refund processed through support"
        }
        resp = self.client.post(f'/api/v1/admin/entitlements/{ent.id}/revoke/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Entitlement status updated
        ent.refresh_from_db()
        self.assertEqual(ent.status, 'REVOKED')

        # Audit log created
        log = ManualAccessLog.objects.filter(student=self.student, action='REVOKE').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin, self.admin)
        self.assertEqual(log.entitlement, ent)
        self.assertEqual(log.reason, "Student requested refund processed through support")

    def test_admin_manual_revoke_fails_without_reason(self):
        """Revocation fails if reason is empty; status remains active."""
        ent = Entitlement.objects.create(
            user=self.student,
            product_type='SUBJECT',
            scope_id=self.subject.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        resp = self.client.post(f'/api/v1/admin/entitlements/{ent.id}/revoke/', {"reason": ""}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", resp.data)

        # Entitlement still active
        ent.refresh_from_db()
        self.assertEqual(ent.status, 'ACTIVE')

    def test_student_cannot_access_admin_entitlements_api(self):
        """Students are rejected with HTTP 403 Forbidden."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        resp = self.client.post('/api/v1/admin/entitlements/grant/', {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_service_level_strictly_enforces_mandatory_reason(self):
        """Direct service calls raise ValueError when reason is missing."""
        from apps.entitlements.services import manual_grant_entitlement, manual_revoke_entitlement

        with self.assertRaises(ValueError):
            manual_grant_entitlement(
                admin_user=self.admin,
                student_user=self.student,
                product_type='CHAPTER',
                scope_id=self.chapter.id,
                reason=""
            )

        ent = Entitlement.objects.create(
            user=self.student,
            product_type='CHAPTER',
            scope_id=self.chapter.id,
            status='ACTIVE'
        )
        with self.assertRaises(ValueError):
            manual_revoke_entitlement(
                admin_user=self.admin,
                entitlement_id=ent.id,
                reason="   "
            )





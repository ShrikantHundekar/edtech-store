from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.entitlements.models import Entitlement
from .models import Product, Price, BundleItem
from .services import calculate_gst_breakdown, calculate_subject_pack_upgrade_credit

User = get_user_model()


class ProductAndPriceModelTests(TestCase):
    def setUp(self):
        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="mathematics")
        self.chapter = Chapter.objects.create(subject=self.subject, chapter_number=1, title="Real Numbers", slug="real-numbers")

    def test_chapter_notes_pricing_in_integer_paise(self):
        product = Product.objects.create(
            title="Class 10 Math Chapter 1 Notes",
            slug="class-10-math-ch1-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.chapter
        )
        # Price is ₹49.00 -> 4900 paise
        price = Price.objects.create(
            product=product,
            amount_paise=4900,
            currency="INR",
            is_current=True
        )

        self.assertEqual(product.current_price_paise, 4900)
        self.assertEqual(product.current_price_inr, 49.00)
        self.assertIsInstance(product.current_price_paise, int)
        self.assertEqual(str(price), "Class 10 Math Chapter 1 Notes: ₹49.00 (4900 paise)")

    def test_subject_pack_pricing(self):
        product = Product.objects.create(
            title="Class 10 Math Subject Pack",
            slug="class-10-math-subject-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.subject
        )
        # Price ₹499.00 -> 49900 paise
        Price.objects.create(
            product=product,
            amount_paise=49900,
            currency="INR",
            is_current=True
        )

        self.assertEqual(product.current_price_paise, 49900)
        self.assertEqual(product.current_price_inr, 499.00)

    def test_monthly_and_annual_passes(self):
        monthly_pass = Product.objects.create(
            title="Class 10 Monthly Pass",
            slug="class-10-monthly-pass",
            product_type=Product.PRODUCT_TYPE_MONTHLY_PASS,
            academic_class=self.academic_class
        )
        Price.objects.create(product=monthly_pass, amount_paise=29900, is_current=True)
        self.assertEqual(monthly_pass.current_price_paise, 29900)

        annual_pass = Product.objects.create(
            title="Class 10 Annual Pass",
            slug="class-10-annual-pass",
            product_type=Product.PRODUCT_TYPE_ANNUAL_PASS,
            academic_class=self.academic_class
        )
        Price.objects.create(product=annual_pass, amount_paise=249900, is_current=True)
        self.assertEqual(annual_pass.current_price_paise, 249900)

    def test_free_sample_price_is_zero(self):
        sample = Product.objects.create(
            title="Free Sample Chapter 1",
            slug="free-sample-ch1",
            product_type=Product.PRODUCT_TYPE_FREE_SAMPLE,
            chapter=self.chapter
        )
        self.assertEqual(sample.current_price_paise, 0)
        self.assertEqual(sample.current_price_inr, 0.0)

    def test_custom_bundle_and_bundle_items(self):
        bundle = Product.objects.create(
            title="Math + Physics Special Bundle",
            slug="math-physics-bundle",
            product_type=Product.PRODUCT_TYPE_BUNDLE
        )
        Price.objects.create(product=bundle, amount_paise=69900, is_current=True)
        
        item = BundleItem.objects.create(
            bundle_product=bundle,
            target_type=BundleItem.TARGET_TYPE_SUBJECT,
            subject=self.subject
        )

        self.assertEqual(bundle.current_price_paise, 69900)
        self.assertEqual(bundle.bundle_items.count(), 1)
        self.assertIn("Bundle", str(item))


class ProductCatalogAPITests(APITestCase):
    def setUp(self):
        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.math = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="mathematics")
        self.science = Subject.objects.create(academic_class=self.academic_class, name="Science", slug="science")

        self.ch1 = Chapter.objects.create(subject=self.math, chapter_number=1, title="Real Numbers", slug="real-numbers", is_free_sample=True)
        self.ch2 = Chapter.objects.create(subject=self.math, chapter_number=2, title="Polynomials", slug="polynomials", is_free_sample=False)
        self.ch3 = Chapter.objects.create(subject=self.science, chapter_number=1, title="Chemical Reactions", slug="chemical-reactions")

        # 1. CHAPTER_NOTES (₹49 -> 4,900 paise)
        self.p_chapter = Product.objects.create(
            title="Math Chapter 2 Notes",
            slug="math-ch2-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            board=self.board,
            academic_class=self.academic_class,
            subject=self.math,
            chapter=self.ch2,
            is_active=True
        )
        Price.objects.create(product=self.p_chapter, amount_paise=4900, is_current=True)

        # 2. SUBJECT_PACK (₹499 -> 49,900 paise)
        self.p_subject = Product.objects.create(
            title="Class 10 Math Subject Pack",
            slug="class-10-math-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            board=self.board,
            academic_class=self.academic_class,
            subject=self.math,
            is_active=True
        )
        Price.objects.create(product=self.p_subject, amount_paise=49900, is_current=True)

        # 3. MONTHLY_PASS (₹299 -> 29,900 paise, 30 days)
        self.p_monthly = Product.objects.create(
            title="Class 10 Monthly Pass",
            slug="class-10-monthly-pass",
            product_type=Product.PRODUCT_TYPE_MONTHLY_PASS,
            board=self.board,
            academic_class=self.academic_class,
            is_active=True
        )
        Price.objects.create(product=self.p_monthly, amount_paise=29900, is_current=True)

        # 4. ANNUAL_PASS (₹2,499 -> 249,900 paise, 365 days)
        self.p_annual = Product.objects.create(
            title="Class 10 Annual Pass",
            slug="class-10-annual-pass",
            product_type=Product.PRODUCT_TYPE_ANNUAL_PASS,
            board=self.board,
            academic_class=self.academic_class,
            is_active=True
        )
        Price.objects.create(product=self.p_annual, amount_paise=249900, is_current=True)

        # 5. BUNDLE (₹699 -> 69,900 paise)
        self.p_bundle = Product.objects.create(
            title="STEM Super Bundle",
            slug="stem-super-bundle",
            product_type=Product.PRODUCT_TYPE_BUNDLE,
            board=self.board,
            is_active=True
        )
        Price.objects.create(product=self.p_bundle, amount_paise=69900, is_current=True)
        BundleItem.objects.create(bundle_product=self.p_bundle, target_type='CHAPTER', chapter=self.ch2)
        BundleItem.objects.create(bundle_product=self.p_bundle, target_type='SUBJECT', subject=self.science)

        # 6. FREE_SAMPLE (₹0 -> 0 paise)
        self.p_free = Product.objects.create(
            title="Free Real Numbers Sample",
            slug="free-real-numbers-sample",
            product_type=Product.PRODUCT_TYPE_FREE_SAMPLE,
            board=self.board,
            academic_class=self.academic_class,
            subject=self.math,
            chapter=self.ch1,
            is_active=True
        )

        # Inactive product (should be hidden)
        self.p_inactive = Product.objects.create(
            title="Archived Old Course",
            slug="archived-old-course",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            is_active=False
        )
        Price.objects.create(product=self.p_inactive, amount_paise=1000, is_current=True)

    def test_list_products_returns_all_active_types(self):
        resp = self.client.get('/api/v1/products/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # 6 active products created, inactive is excluded
        self.assertEqual(len(resp.data), 6)
        slugs = [p['slug'] for p in resp.data]
        self.assertNotIn("archived-old-course", slugs)
        self.assertIn("math-ch2-notes", slugs)
        self.assertIn("class-10-math-pack", slugs)
        self.assertIn("class-10-monthly-pass", slugs)
        self.assertIn("class-10-annual-pass", slugs)
        self.assertIn("stem-super-bundle", slugs)
        self.assertIn("free-real-numbers-sample", slugs)

    def test_filter_products_by_type(self):
        resp = self.client.get('/api/v1/products/?product_type=SUBJECT_PACK')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['product_type'], 'SUBJECT_PACK')
        self.assertEqual(resp.data[0]['slug'], 'class-10-math-pack')

    def test_filter_products_by_class(self):
        resp = self.client.get(f'/api/v1/products/?class_id={self.academic_class.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 5 products are tied to class 10 (chapter, subject, monthly, annual, free sample)
        self.assertEqual(len(resp.data), 5)

    def test_chapter_notes_detail_and_gst_breakdown(self):
        resp = self.client.get(f'/api/v1/products/{self.p_chapter.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['title'], "Math Chapter 2 Notes")
        self.assertEqual(data['product_type'], "CHAPTER_NOTES")
        self.assertEqual(data['price_paise'], 4900)
        self.assertEqual(data['price_inr'], 49.00)
        self.assertEqual(data['access_duration'], "Lifetime")

        # Inclusions: Chapter 2
        self.assertEqual(len(data['inclusions']), 1)
        self.assertEqual(data['inclusions'][0]['id'], self.ch2.id)
        self.assertEqual(data['inclusions'][0]['title'], "Polynomials")

        # 18% inclusive GST split:
        # Base taxable = round(4900 / 1.18) = 4153
        # Total GST = 4900 - 4153 = 747
        # CGST = 374, SGST = 373
        gst = data['gst_breakdown']
        self.assertEqual(gst['price_inclusive_paise'], 4900)
        self.assertEqual(gst['base_taxable_paise'], 4153)
        self.assertEqual(gst['total_gst_paise'], 747)
        self.assertEqual(gst['cgst_paise'], 374)
        self.assertEqual(gst['sgst_paise'], 373)
        self.assertEqual(gst['cgst_paise'] + gst['sgst_paise'], gst['total_gst_paise'])
        self.assertEqual(gst['base_taxable_paise'] + gst['total_gst_paise'], 4900)

    def test_subject_pack_detail_and_inclusions(self):
        resp = self.client.get(f'/api/v1/products/{self.p_subject.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 49900)
        self.assertEqual(data['price_inr'], 499.00)
        self.assertEqual(data['access_duration'], "Lifetime")

        # Inclusions: chapters 1 and 2 under Math
        self.assertEqual(len(data['inclusions']), 2)
        ch_ids = [c['id'] for c in data['inclusions']]
        self.assertIn(self.ch1.id, ch_ids)
        self.assertIn(self.ch2.id, ch_ids)

        # 18% GST split matching specification exactly:
        # Base taxable = 42288 paise (₹422.88)
        # Total GST = 7612 paise (₹76.12)
        # CGST = 3806 paise (₹38.06)
        # SGST = 3806 paise (₹38.06)
        gst = data['gst_breakdown']
        self.assertEqual(gst['price_inclusive_paise'], 49900)
        self.assertEqual(gst['base_taxable_paise'], 42288)
        self.assertEqual(gst['total_gst_paise'], 7612)
        self.assertEqual(gst['cgst_paise'], 3806)
        self.assertEqual(gst['sgst_paise'], 3806)

    def test_monthly_pass_detail(self):
        resp = self.client.get(f'/api/v1/products/{self.p_monthly.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 29900)
        self.assertEqual(data['access_duration'], "30 Days")
        # Inclusions: list of subjects in class
        self.assertGreaterEqual(len(data['inclusions']), 2)

    def test_annual_pass_detail(self):
        resp = self.client.get(f'/api/v1/products/{self.p_annual.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 249900)
        self.assertEqual(data['access_duration'], "365 Days")

    def test_bundle_detail_and_inclusions(self):
        resp = self.client.get(f'/api/v1/products/{self.p_bundle.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 69900)
        self.assertEqual(data['access_duration'], "Lifetime")
        self.assertEqual(len(data['inclusions']), 2)
        types = [item['target_type'] for item in data['inclusions']]
        self.assertIn('CHAPTER', types)
        self.assertIn('SUBJECT', types)

    def test_free_sample_detail_zero_price(self):
        resp = self.client.get(f'/api/v1/products/{self.p_free.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 0)
        self.assertEqual(data['price_inr'], 0.0)
        self.assertEqual(data['access_duration'], "Lifetime")
        self.assertEqual(data['gst_breakdown']['price_inclusive_paise'], 0)
        self.assertEqual(data['gst_breakdown']['total_gst_paise'], 0)

    def test_nonexistent_product_returns_404(self):
        resp = self.client.get('/api/v1/products/99999/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ProductOwnershipAndOverlappingCartTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student_buyer@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)

        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.math = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="math")
        self.science = Subject.objects.create(academic_class=self.academic_class, name="Science", slug="science")

        self.ch_math_1 = Chapter.objects.create(subject=self.math, chapter_number=1, title="Real Numbers", slug="real-numbers")
        self.ch_math_2 = Chapter.objects.create(subject=self.math, chapter_number=2, title="Polynomials", slug="polynomials")
        self.ch_sci_1 = Chapter.objects.create(subject=self.science, chapter_number=1, title="Chemical Reactions", slug="chem-react")

        # Products
        self.prod_ch_math_1 = Product.objects.create(
            title="Math Chapter 1 Notes",
            slug="prod-math-ch1",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.ch_math_1,
            subject=self.math,
            academic_class=self.academic_class,
            board=self.board
        )
        Price.objects.create(product=self.prod_ch_math_1, amount_paise=4900, is_current=True)

        self.prod_ch_math_2 = Product.objects.create(
            title="Math Chapter 2 Notes",
            slug="prod-math-ch2",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.ch_math_2,
            subject=self.math,
            academic_class=self.academic_class,
            board=self.board
        )
        Price.objects.create(product=self.prod_ch_math_2, amount_paise=4900, is_current=True)

        self.prod_math_pack = Product.objects.create(
            title="Mathematics Subject Pack",
            slug="prod-math-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.math,
            academic_class=self.academic_class,
            board=self.board
        )
        Price.objects.create(product=self.prod_math_pack, amount_paise=49900, is_current=True)

        self.prod_sci_pack = Product.objects.create(
            title="Science Subject Pack",
            slug="prod-sci-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.science,
            academic_class=self.academic_class,
            board=self.board
        )
        Price.objects.create(product=self.prod_sci_pack, amount_paise=49900, is_current=True)

        self.prod_class_pass = Product.objects.create(
            title="Class 10 Monthly Pass",
            slug="prod-class-10-pass",
            product_type=Product.PRODUCT_TYPE_MONTHLY_PASS,
            academic_class=self.academic_class,
            board=self.board
        )
        Price.objects.create(product=self.prod_class_pass, amount_paise=29900, is_current=True)

    def test_default_state_is_buy(self):
        # Unauthenticated user
        resp = self.client.get(f'/api/v1/products/{self.prod_ch_math_1.id}/ownership/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['purchase_state'], 'BUY')
        self.assertTrue(resp.data['can_purchase'])

        # Authenticated student with no entitlements
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp_auth = self.client.get(f'/api/v1/products/{self.prod_ch_math_1.id}/ownership/')
        self.assertEqual(resp_auth.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_auth.data['purchase_state'], 'BUY')
        self.assertTrue(resp_auth.data['can_purchase'])

    def test_chapter_ownership_marks_owned_and_subject_pack_upgrade(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Grant entitlement for Math Chapter 1
        Entitlement.objects.create(
            user=self.user,
            product_type='CHAPTER',
            scope_id=self.ch_math_1.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        # 1. Math Chapter 1 is now OWNED
        resp_ch1 = self.client.get(f'/api/v1/products/{self.prod_ch_math_1.id}/ownership/')
        self.assertEqual(resp_ch1.data['purchase_state'], 'OWNED')
        self.assertFalse(resp_ch1.data['can_purchase'])

        # 2. Math Chapter 2 (un-owned) is still BUY
        resp_ch2 = self.client.get(f'/api/v1/products/{self.prod_ch_math_2.id}/ownership/')
        self.assertEqual(resp_ch2.data['purchase_state'], 'BUY')
        self.assertTrue(resp_ch2.data['can_purchase'])

        # 3. Math Subject Pack transitions to UPGRADE state (eligible for upgrade credit)
        resp_pack = self.client.get(f'/api/v1/products/{self.prod_math_pack.id}/ownership/')
        self.assertEqual(resp_pack.data['purchase_state'], 'UPGRADE')
        self.assertTrue(resp_pack.data['can_purchase'])

    def test_subject_pack_ownership_marks_pack_and_all_chapters_owned(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Grant entitlement for Math Subject Pack
        Entitlement.objects.create(
            user=self.user,
            product_type='SUBJECT',
            scope_id=self.math.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        # 1. Subject Pack is OWNED
        resp_pack = self.client.get(f'/api/v1/products/{self.prod_math_pack.id}/ownership/')
        self.assertEqual(resp_pack.data['purchase_state'], 'OWNED')
        self.assertFalse(resp_pack.data['can_purchase'])

        # 2. Both individual chapters under Math are now OWNED (via Subject Pack)
        resp_ch1 = self.client.get(f'/api/v1/products/{self.prod_ch_math_1.id}/ownership/')
        self.assertEqual(resp_ch1.data['purchase_state'], 'OWNED')
        self.assertFalse(resp_ch1.data['can_purchase'])
        self.assertIn("Subject Pack", resp_ch1.data['reason'])

        resp_ch2 = self.client.get(f'/api/v1/products/{self.prod_ch_math_2.id}/ownership/')
        self.assertEqual(resp_ch2.data['purchase_state'], 'OWNED')
        self.assertFalse(resp_ch2.data['can_purchase'])

    def test_class_pass_ownership_marks_chapters_and_subjects_unlocked_via_pass(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Grant active Class Pass for Class 10
        Entitlement.objects.create(
            user=self.user,
            product_type='CLASS_PASS',
            scope_id=self.academic_class.id,
            access_type='TIME_BOUND',
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=29),
            status='ACTIVE'
        )

        # 1. Chapter in Class 10 is UNLOCKED_VIA_PASS
        resp_ch = self.client.get(f'/api/v1/products/{self.prod_ch_math_1.id}/ownership/')
        self.assertEqual(resp_ch.data['purchase_state'], 'UNLOCKED_VIA_PASS')
        self.assertFalse(resp_ch.data['can_purchase'])

        # 2. Subject in Class 10 is UNLOCKED_VIA_PASS
        resp_sub = self.client.get(f'/api/v1/products/{self.prod_math_pack.id}/ownership/')
        self.assertEqual(resp_sub.data['purchase_state'], 'UNLOCKED_VIA_PASS')
        self.assertFalse(resp_sub.data['can_purchase'])

    def test_cart_validation_rejects_already_owned_items(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Grant Math Chapter 1
        Entitlement.objects.create(
            user=self.user,
            product_type='CHAPTER',
            scope_id=self.ch_math_1.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        # Try to validate cart with Math Chapter 1
        resp = self.client.post('/api/v1/cart/validate/', {
            "items": [{"product_id": self.prod_ch_math_1.id}]
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(resp.data['valid'])
        self.assertIn("Owned", str(resp.data['errors']))

    def test_cart_validation_rejects_items_unlocked_by_class_pass(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Grant active Class Pass
        Entitlement.objects.create(
            user=self.user,
            product_type='CLASS_PASS',
            scope_id=self.academic_class.id,
            access_type='TIME_BOUND',
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=29),
            status='ACTIVE'
        )

        resp = self.client.post('/api/v1/cart/validate/', {
            "items": [{"product_id": self.prod_math_pack.id}]
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unlocked with Class Pass", str(resp.data['errors']))

    def test_cart_validation_rejects_intra_cart_overlap_pack_and_chapter(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # User tries to buy both Math Subject Pack AND Math Chapter 1 in the SAME cart
        resp = self.client.post('/api/v1/cart/validate/', {
            "items": [
                {"product_id": self.prod_math_pack.id},
                {"product_id": self.prod_ch_math_1.id}
            ]
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("together with its Subject Pack", str(resp.data['errors']))

    def test_cart_validation_rejects_intra_cart_overlap_pass_and_subject(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # User tries to buy both Class Pass AND Subject Pack for that class in the SAME cart
        resp = self.client.post('/api/v1/cart/validate/', {
            "items": [
                {"product_id": self.prod_class_pass.id},
                {"product_id": self.prod_sci_pack.id}
            ]
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already unlocked by the Class Pass", str(resp.data['errors']))

    def test_cart_validation_accepts_valid_non_overlapping_items(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # User buys Science Pack + Math Chapter 1 (distinct scopes, no overlap)
        resp = self.client.post('/api/v1/cart/validate/', {
            "items": [
                {"product_id": self.prod_sci_pack.id},
                {"product_id": self.prod_ch_math_1.id}
            ]
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['valid'])
        self.assertEqual(resp.data['items_count'], 2)


class SubjectPackUpgradeCreditTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="upgrader@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)

        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.math = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="math")

        # 5 chapters under Math
        self.chapters = []
        for i in range(1, 6):
            ch = Chapter.objects.create(
                subject=self.math,
                chapter_number=i,
                title=f"Math Chapter {i}",
                slug=f"math-ch-{i}"
            )
            self.chapters.append(ch)

            # Product for each chapter (₹49 -> 4,900 paise)
            p = Product.objects.create(
                title=f"Math Ch {i} Notes",
                slug=f"math-ch-{i}-notes",
                product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
                subject=self.math,
                chapter=ch,
                academic_class=self.academic_class,
                board=self.board
            )
            Price.objects.create(product=p, amount_paise=4900, is_current=True)

        # Subject Pack (₹499 -> 49,900 paise)
        self.subject_pack = Product.objects.create(
            title="Class 10 Math Subject Pack",
            slug="class-10-math-subject-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.math,
            academic_class=self.academic_class,
            board=self.board
        )
        Price.objects.create(product=self.subject_pack, amount_paise=49900, is_current=True)

    def test_zero_credit_when_no_chapters_owned(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp = self.client.post(f'/api/v1/products/{self.subject_pack.id}/calculate-price/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['base_price_paise'], 49900)
        self.assertEqual(data['upgrade_credit_paise'], 0)
        self.assertEqual(data['payable_price_paise'], 49900)
        self.assertEqual(data['payable_price_inr'], 499.0)
        self.assertEqual(data['owned_chapters_count'], 0)
        self.assertEqual(len(data['owned_chapters']), 0)

    def test_credit_deduction_for_two_owned_chapters(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Student owns Chapter 1 (₹49) and Chapter 2 (₹49) -> Total credit ₹98 (9,800 paise)
        Entitlement.objects.create(
            user=self.user,
            product_type='CHAPTER',
            scope_id=self.chapters[0].id,
            access_type='LIFETIME',
            status='ACTIVE'
        )
        Entitlement.objects.create(
            user=self.user,
            product_type='CHAPTER',
            scope_id=self.chapters[1].id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        resp = self.client.post(f'/api/v1/products/{self.subject_pack.id}/calculate-price/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        # Upgrade Price = max(0, 49900 - 9800) = 40100 paise (₹401.00)
        self.assertEqual(data['base_price_paise'], 49900)
        self.assertEqual(data['upgrade_credit_paise'], 9800)
        self.assertEqual(data['upgrade_credit_inr'], 98.0)
        self.assertEqual(data['payable_price_paise'], 40100)
        self.assertEqual(data['payable_price_inr'], 401.0)
        self.assertEqual(data['owned_chapters_count'], 2)

        # Inclusions in credit
        owned_ids = [c['chapter_id'] for c in data['owned_chapters']]
        self.assertIn(self.chapters[0].id, owned_ids)
        self.assertIn(self.chapters[1].id, owned_ids)

        # 18% GST recomputed on ₹401.00:
        # Base taxable = round(40100 / 1.18) = 33983 paise
        # Total GST = 40100 - 33983 = 6117 paise
        # CGST = round(6117 / 2) = 3058, SGST = 6117 - 3058 = 3059
        gst = data['gst_breakdown']
        self.assertEqual(gst['price_inclusive_paise'], 40100)
        self.assertEqual(gst['base_taxable_paise'], 33983)
        self.assertEqual(gst['total_gst_paise'], 6117)
        self.assertEqual(gst['cgst_paise'], 3058)
        self.assertEqual(gst['sgst_paise'], 3059)
        self.assertEqual(gst['cgst_paise'] + gst['sgst_paise'], gst['total_gst_paise'])


    def test_price_floors_at_zero_when_credits_exceed_pack_price(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Set Subject Pack price to ₹100 (10,000 paise)
        Price.objects.filter(product=self.subject_pack).update(is_current=False)
        Price.objects.create(product=self.subject_pack, amount_paise=10000, is_current=True)

        # Student owns 3 chapters (3 * 4900 = 14,700 paise > 10,000 paise)
        for i in range(3):
            Entitlement.objects.create(
                user=self.user,
                product_type='CHAPTER',
                scope_id=self.chapters[i].id,
                access_type='LIFETIME',
                status='ACTIVE'
            )

        resp = self.client.post(f'/api/v1/products/{self.subject_pack.id}/calculate-price/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        # Upgrade Price = max(0, 10000 - 14700) = 0 paise (floors at 0)
        self.assertEqual(data['base_price_paise'], 10000)
        self.assertEqual(data['payable_price_paise'], 0)
        self.assertEqual(data['payable_price_inr'], 0.0)
        self.assertEqual(data['upgrade_credit_paise'], 10000)  # Capped at base price
        self.assertEqual(data['total_credit_available_paise'], 14700)
        self.assertEqual(data['gst_breakdown']['price_inclusive_paise'], 0)
        self.assertEqual(data['gst_breakdown']['total_gst_paise'], 0)

    def test_unauthenticated_user_receives_full_price_without_credit(self):
        resp = self.client.get(f'/api/v1/products/{self.subject_pack.id}/calculate-price/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['upgrade_credit_paise'], 0)
        self.assertEqual(resp.data['payable_price_paise'], 49900)


class MultiItemCartPriceRecalculationTests(APITestCase):
    def setUp(self):
        self.board = Board.objects.create(name="CBSE Cart", slug="cbse-cart")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10-cart")
        self.subject_math = Subject.objects.create(
            academic_class=self.academic_class,
            name="Mathematics",
            slug="math-cart"
        )
        self.subject_sci = Subject.objects.create(
            academic_class=self.academic_class,
            name="Science",
            slug="sci-cart"
        )
        self.ch_math_1 = Chapter.objects.create(
            subject=self.subject_math,
            chapter_number=1,
            title="Real Numbers"
        )
        self.ch_sci_1 = Chapter.objects.create(
            subject=self.subject_sci,
            chapter_number=1,
            title="Chemical Reactions"
        )

        # Products
        self.prod_ch_math = Product.objects.create(
            title="Class 10 Math Chapter 1",
            slug="class-10-math-ch-1",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.ch_math_1,
            is_active=True
        )
        Price.objects.create(product=self.prod_ch_math, amount_paise=4900, is_current=True)

        self.prod_ch_sci = Product.objects.create(
            title="Class 10 Science Chapter 1",
            slug="class-10-sci-ch-1",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.ch_sci_1,
            is_active=True
        )
        Price.objects.create(product=self.prod_ch_sci, amount_paise=4900, is_current=True)

        self.prod_sci_pack = Product.objects.create(
            title="Class 10 Science Full Pack",
            slug="class-10-sci-full-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.subject_sci,
            is_active=True
        )
        Price.objects.create(product=self.prod_sci_pack, amount_paise=49900, is_current=True)

        self.user = User.objects.create_user(
            email="cartstudent@example.com",
            password="StrongPassword123!",
            role="STUDENT"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)

    def test_cart_validation_completely_ignores_client_submitted_prices(self):
        """
        US-CART-01: Given a modified client payload that attempts to send a tampered price
        (e.g. price: 1, price_paise: 10), the server completely ignores the client price
        and recomputes strictly from source database records.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        payload = {
            "items": [
                {
                    "product_id": self.prod_ch_math.id,
                    "price": 1,
                    "price_paise": 100,
                    "amount": 0,
                    "final_price": 50
                },
                {
                    "product_id": self.prod_ch_sci.id,
                    "price": 0,
                    "price_paise": 10,
                    "amount": 0
                }
            ]
        }

        resp = self.client.post('/api/v1/cart/validate/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertTrue(data['valid'])
        self.assertEqual(data['items_count'], 2)

        # Check line items
        items = data['items']
        self.assertEqual(len(items), 2)
        # Math chapter line item: strictly 4900 paise
        math_item = next(item for item in items if item['product_id'] == self.prod_ch_math.id)
        self.assertEqual(math_item['base_price_paise'], 4900)
        self.assertEqual(math_item['final_price_paise'], 4900)
        self.assertEqual(math_item['upgrade_credit_paise'], 0)

        # Sci chapter line item: strictly 4900 paise
        sci_item = next(item for item in items if item['product_id'] == self.prod_ch_sci.id)
        self.assertEqual(sci_item['base_price_paise'], 4900)
        self.assertEqual(sci_item['final_price_paise'], 4900)
        self.assertEqual(sci_item['upgrade_credit_paise'], 0)

        # Cart pricing totals
        pricing = data['pricing']
        self.assertEqual(pricing['total_base_price_paise'], 9800)
        self.assertEqual(pricing['total_upgrade_credit_paise'], 0)
        self.assertEqual(pricing['subtotal_paise'], 9800)
        self.assertEqual(pricing['subtotal_inr'], 98.0)

        # GST breakdown on 9800
        gst = pricing['gst_breakdown']
        self.assertEqual(gst['price_inclusive_paise'], 9800)
        self.assertEqual(gst['base_taxable_paise'] + gst['total_gst_paise'], 9800)
        self.assertEqual(gst['cgst_paise'] + gst['sgst_paise'], gst['total_gst_paise'])

    def test_cart_validation_applies_subject_pack_upgrade_credit(self):
        """
        Cart validation applies upgrade credit dynamically when student owns prior chapters.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Grant student ownership of Science Chapter 1
        Entitlement.objects.create(
            user=self.user,
            product_type='CHAPTER',
            scope_id=self.ch_sci_1.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        # Cart contains: Math Chapter 1 (4900 paise) + Science Full Pack (49900 - 4900 credit = 45000 paise)
        payload = {
            "items": [
                {"product_id": self.prod_ch_math.id},
                {"product_id": self.prod_sci_pack.id}
            ]
        }

        resp = self.client.post('/api/v1/cart/validate/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        items = data['items']
        sci_pack_item = next(item for item in items if item['product_id'] == self.prod_sci_pack.id)
        self.assertEqual(sci_pack_item['base_price_paise'], 49900)
        self.assertEqual(sci_pack_item['upgrade_credit_paise'], 4900)
        self.assertEqual(sci_pack_item['final_price_paise'], 45000)

        math_item = next(item for item in items if item['product_id'] == self.prod_ch_math.id)
        self.assertEqual(math_item['final_price_paise'], 4900)

        pricing = data['pricing']
        self.assertEqual(pricing['total_base_price_paise'], 54800)
        self.assertEqual(pricing['total_upgrade_credit_paise'], 4900)
        self.assertEqual(pricing['subtotal_paise'], 49900)

    def test_cart_validation_rejects_inactive_product(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Deactivate product
        self.prod_ch_sci.is_active = False
        self.prod_ch_sci.save()

        payload = {
            "items": [
                {"product_id": self.prod_ch_math.id},
                {"product_id": self.prod_ch_sci.id}
            ]
        }

        resp = self.client.post('/api/v1/cart/validate/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(resp.data['valid'])
        self.assertIn("no longer active", str(resp.data['errors']))





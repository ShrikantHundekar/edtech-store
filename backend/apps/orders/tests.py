from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.products.models import Product, Price
from apps.entitlements.models import Entitlement
from .models import Order, OrderItem, Coupon
from .services import redeem_coupon, validate_and_apply_coupon, create_order
from .gst import calculate_inclusive_gst, calculate_gst_breakdown

User = get_user_model()


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student_test@example.com",
            full_name="Student Tester",
            password="TestPassword@123"
        )
        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="math")
        self.chapter = Chapter.objects.create(subject=self.subject, chapter_number=1, title="Real Numbers", slug="real-numbers")

        self.product = Product.objects.create(
            title="Class 10 Math Chapter 1",
            slug="ch1-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.chapter
        )
        Price.objects.create(product=self.product, amount_paise=4900, is_current=True)

    def test_order_creation_and_breakdown(self):
        # Order for ₹49.00 inclusive (4900 paise)
        # Base taxable = round(4900 / 1.18) = 4153 paise
        # GST = 4900 - 4153 = 747 paise
        order = Order.objects.create(
            user=self.user,
            order_number=Order.generate_order_number(),
            razorpay_order_id="order_test_12345",
            status=Order.STATUS_PENDING,
            gross_amount_paise=4900,
            upgrade_discount_paise=0,
            coupon_discount_paise=0,
            taxable_base_paise=4153,
            gst_amount_paise=747,
            net_payable_paise=4900
        )

        item = OrderItem.objects.create(
            order=order,
            product=self.product,
            unit_price_paise=4900,
            upgrade_credit_paise=0,
            net_price_paise=4900
        )

        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.net_payable_paise, 4900)
        self.assertEqual(order.net_payable_inr, 49.00)
        self.assertEqual(order.taxable_base_inr, 41.53)
        self.assertEqual(order.gst_amount_inr, 7.47)
        self.assertEqual(item.net_price_paise, 4900)
        self.assertIn("Pending", str(order))

    def test_order_status_transitions(self):
        order = Order.objects.create(
            user=self.user,
            order_number=Order.generate_order_number(),
            status=Order.STATUS_PENDING,
            net_payable_paise=4900
        )
        self.assertEqual(order.status, Order.STATUS_PENDING)
        
        # Transition to PAID
        order.status = Order.STATUS_PAID
        order.save()
        self.assertEqual(order.status, Order.STATUS_PAID)

        # Transition to FAILED
        order.status = Order.STATUS_FAILED
        order.save()
        self.assertEqual(order.status, Order.STATUS_FAILED)


class CouponModelTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.flat_coupon = Coupon.objects.create(
            code="FLAT50",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=5000,  # ₹50 = 5000 paise
            min_order_paise=10000,  # ₹100 = 10000 paise
            usage_limit=100,
            times_used=0,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30),
            is_active=True
        )

        self.percent_coupon = Coupon.objects.create(
            code="SAVE10",
            discount_type=Coupon.DISCOUNT_TYPE_PERCENTAGE,
            discount_value=10,  # 10%
            min_order_paise=0,
            max_discount_paise=5000,  # Max ₹50 cap
            usage_limit=50,
            times_used=0,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30),
            is_active=True
        )

    def test_flat_coupon_discount_calculation(self):
        # Cart subtotal ₹150 (15000 paise) >= min_order (10000 paise)
        discount = self.flat_coupon.calculate_discount(15000)
        self.assertEqual(discount, 5000)

        # Cart subtotal below min_order -> 0
        discount_below = self.flat_coupon.calculate_discount(8000)
        self.assertEqual(discount_below, 0)

        # Flat discount exceeding subtotal floors at subtotal
        big_coupon = Coupon.objects.create(
            code="BIG200",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=20000,  # ₹200
            min_order_paise=0,
            valid_until=self.now + timedelta(days=10)
        )
        self.assertEqual(big_coupon.calculate_discount(15000), 15000)

    def test_percentage_coupon_discount_calculation(self):
        # 10% of ₹499 (49900 paise) = 4990 paise (< max cap of 5000 paise)
        discount = self.percent_coupon.calculate_discount(49900)
        self.assertEqual(discount, 4990)

    def test_percentage_coupon_with_max_discount_cap(self):
        # 10% of ₹1000 (100000 paise) = 10000 paise -> capped at 5000 paise
        discount = self.percent_coupon.calculate_discount(100000)
        self.assertEqual(discount, 5000)

    def test_coupon_validate_for_cart_success(self):
        is_valid, error, discount = self.flat_coupon.validate_for_cart(20000)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        self.assertEqual(discount, 5000)

    def test_coupon_validate_for_cart_min_order_failure(self):
        is_valid, error, discount = self.flat_coupon.validate_for_cart(5000)
        self.assertFalse(is_valid)
        self.assertIn("must be at least ₹100.00", error)
        self.assertEqual(discount, 0)

    def test_coupon_expired_rejection(self):
        expired_coupon = Coupon.objects.create(
            code="EXPIRED",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=1000,
            valid_from=self.now - timedelta(days=10),
            valid_until=self.now - timedelta(days=1),
            is_active=True
        )
        is_valid, error, discount = expired_coupon.validate_for_cart(10000)
        self.assertFalse(is_valid)
        self.assertIn("expired", error)
        self.assertEqual(discount, 0)

    def test_coupon_usage_limit_exhausted_rejection(self):
        exhausted_coupon = Coupon.objects.create(
            code="EXHAUSTED",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=1000,
            usage_limit=10,
            times_used=10,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=10),
            is_active=True
        )
        is_valid, error, discount = exhausted_coupon.validate_for_cart(10000)
        self.assertFalse(is_valid)
        self.assertIn("maximum usage limit", error)
        self.assertEqual(discount, 0)

    def test_coupon_inactive_rejection(self):
        inactive_coupon = Coupon.objects.create(
            code="DISABLED",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=1000,
            is_active=False,
            valid_until=self.now + timedelta(days=10)
        )
        is_valid, error, discount = inactive_coupon.validate_for_cart(10000)
        self.assertFalse(is_valid)
        self.assertIn("inactive", error)
        self.assertEqual(discount, 0)

    def test_coupon_future_valid_from_rejection(self):
        future_coupon = Coupon.objects.create(
            code="FUTURE",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=1000,
            valid_from=self.now + timedelta(days=5),
            valid_until=self.now + timedelta(days=15),
            is_active=True
        )
        is_valid, error, discount = future_coupon.validate_for_cart(10000)
        self.assertFalse(is_valid)
        self.assertIn("not yet valid", error)
        self.assertEqual(discount, 0)


class CouponApplyAPITests(APITestCase):
    def setUp(self):
        self.now = timezone.now()
        self.user = User.objects.create_user(
            email="coupon_student@example.com",
            password="StrongPassword123!",
            role="STUDENT"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)

        self.board = Board.objects.create(name="CBSE Coupon", slug="cbse-coupon")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10-coupon")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Math", slug="math-coupon")
        self.chapter = Chapter.objects.create(subject=self.subject, chapter_number=1, title="Real Numbers")
        self.product = Product.objects.create(
            title="Class 10 Math Chapter 1",
            slug="ch1-coupon",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.chapter
        )
        Price.objects.create(product=self.product, amount_paise=4900, is_current=True)

        self.flat_coupon = Coupon.objects.create(
            code="DISCOUNT50",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=5000,  # ₹50 = 5000 paise
            min_order_paise=10000,  # ₹100
            usage_limit=10,
            times_used=0,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30),
            is_active=True
        )

        self.percent_coupon = Coupon.objects.create(
            code="SAVE10",
            discount_type=Coupon.DISCOUNT_TYPE_PERCENTAGE,
            discount_value=10,  # 10%
            min_order_paise=0,
            max_discount_paise=2000,  # Max ₹20
            usage_limit=10,
            times_used=0,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30),
            is_active=True
        )

        self.expired_coupon = Coupon.objects.create(
            code="EXPIRED20",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=2000,
            valid_from=self.now - timedelta(days=10),
            valid_until=self.now - timedelta(days=1),
            is_active=True
        )

        self.exhausted_coupon = Coupon.objects.create(
            code="MAXEDOUT",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=2000,
            usage_limit=5,
            times_used=5,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=10),
            is_active=True
        )

    def test_apply_flat_coupon_success(self):
        """
        US-CART-02: Given an active coupon with code DISCOUNT50 (flat ₹50 off),
        When applied to a cart with subtotal ₹200 (20000 paise),
        Then the cart total becomes ₹150 (15000 paise).
        """
        payload = {
            "code": "DISCOUNT50",
            "cart_subtotal_paise": 20000
        }
        resp = self.client.post('/api/v1/coupons/apply/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertTrue(data['valid'])
        self.assertEqual(data['subtotal_paise'], 20000)
        self.assertEqual(data['subtotal_inr'], 200.0)
        self.assertEqual(data['discount_paise'], 5000)
        self.assertEqual(data['discount_inr'], 50.0)
        self.assertEqual(data['net_payable_paise'], 15000)
        self.assertEqual(data['net_payable_inr'], 150.0)
        self.assertEqual(data['gst_breakdown']['price_inclusive_paise'], 15000)

    def test_apply_percentage_coupon_success_with_cap(self):
        # 10% of ₹300 (30000 paise) = 3000 paise -> capped at max_discount_paise (2000 paise = ₹20)
        payload = {
            "code": "SAVE10",
            "cart_subtotal_paise": 30000
        }
        resp = self.client.post('/api/v1/coupons/apply/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertTrue(data['valid'])
        self.assertEqual(data['discount_paise'], 2000)
        self.assertEqual(data['net_payable_paise'], 28000)

    def test_apply_coupon_with_cart_items_payload(self):
        # Server recalculates subtotal from items (4900 paise)
        # DISCOUNT50 requires min order ₹100 (10000 paise), so 4900 is rejected
        payload = {
            "code": "DISCOUNT50",
            "items": [{"product_id": self.product.id}]
        }
        resp = self.client.post('/api/v1/coupons/apply/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(resp.data['valid'])
        self.assertIn("must be at least ₹100.00", resp.data['error'])

    def test_apply_expired_coupon_rejected(self):
        """
        US-CART-02: Expired coupon returns HTTP 400 with specific error message.
        """
        payload = {
            "code": "EXPIRED20",
            "cart_subtotal_paise": 15000
        }
        resp = self.client.post('/api/v1/coupons/apply/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(resp.data['valid'])
        self.assertIn("expired", resp.data['error'].lower())

    def test_apply_usage_limit_exhausted_rejected(self):
        """
        US-CART-02: Exceeded usage limit returns HTTP 400 with specific error message.
        """
        payload = {
            "code": "MAXEDOUT",
            "cart_subtotal_paise": 15000
        }
        resp = self.client.post('/api/v1/coupons/apply/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(resp.data['valid'])
        self.assertIn("usage limit", resp.data['error'].lower())

    def test_apply_nonexistent_coupon_rejected(self):
        payload = {
            "code": "DOESNOTEXIST",
            "cart_subtotal_paise": 15000
        }
        resp = self.client.post('/api/v1/coupons/apply/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(resp.data['valid'])
        self.assertIn("Invalid coupon code", resp.data['error'])

    def test_redeem_coupon_atomically_increments_times_used(self):
        """
        Criteria: Atomically increments times_used upon completed order.
        """
        self.assertEqual(self.flat_coupon.times_used, 0)
        updated_coupon = redeem_coupon(self.flat_coupon)
        self.assertEqual(updated_coupon.times_used, 1)

        # Redeem again
        updated_coupon = redeem_coupon(self.flat_coupon.id)
        self.assertEqual(updated_coupon.times_used, 2)


class GSTTaxSplitEngineTests(TestCase):
    def test_gst_breakdown_zero_or_negative_price(self):
        res = calculate_inclusive_gst(0)
        self.assertEqual(res['price_inclusive_paise'], 0)
        self.assertEqual(res['base_taxable_paise'], 0)
        self.assertEqual(res['total_gst_paise'], 0)
        self.assertEqual(res['cgst_paise'], 0)
        self.assertEqual(res['sgst_paise'], 0)

        res_neg = calculate_inclusive_gst(-500)
        self.assertEqual(res_neg['price_inclusive_paise'], 0)
        self.assertEqual(res_neg['base_taxable_paise'], 0)

    def test_gst_breakdown_chapter_notes_49_inr(self):
        """
        Chapter notes ₹49.00 (4900 paise):
        Base Taxable = round(4900 / 1.18) = 4153 paise
        Total GST = 4900 - 4153 = 747 paise
        CGST = round(747 / 2) = 374 paise
        SGST = 747 - 374 = 373 paise
        """
        res = calculate_inclusive_gst(4900)
        self.assertEqual(res['price_inclusive_paise'], 4900)
        self.assertEqual(res['base_taxable_paise'], 4153)
        self.assertEqual(res['total_gst_paise'], 747)
        self.assertEqual(res['cgst_paise'], 374)
        self.assertEqual(res['sgst_paise'], 373)
        self.assertEqual(res['base_taxable_paise'] + res['total_gst_paise'], 4900)
        self.assertEqual(res['cgst_paise'] + res['sgst_paise'], 747)
        self.assertEqual(res['price_inclusive_inr'], 49.00)
        self.assertEqual(res['base_taxable_inr'], 41.53)
        self.assertEqual(res['total_gst_inr'], 7.47)
        self.assertEqual(res['cgst_inr'], 3.74)
        self.assertEqual(res['sgst_inr'], 3.73)

    def test_gst_breakdown_subject_pack_499_inr(self):
        """
        US-CART-03: Given ₹499.00 (49,900 paise):
        Base Taxable = round(49900 / 1.18) = 42288 paise (₹422.88)
        Total GST = 49900 - 42288 = 7612 paise (₹76.12)
        CGST (9%) = 3806 paise (₹38.06)
        SGST (9%) = 3806 paise (₹38.06)
        """
        res = calculate_inclusive_gst(49900)
        self.assertEqual(res['price_inclusive_paise'], 49900)
        self.assertEqual(res['base_taxable_paise'], 42288)
        self.assertEqual(res['total_gst_paise'], 7612)
        self.assertEqual(res['cgst_paise'], 3806)
        self.assertEqual(res['sgst_paise'], 3806)
        self.assertEqual(res['base_taxable_paise'] + res['total_gst_paise'], 49900)
        self.assertEqual(res['cgst_paise'] + res['sgst_paise'], 7612)
        self.assertEqual(res['base_taxable_inr'], 422.88)
        self.assertEqual(res['total_gst_inr'], 76.12)
        self.assertEqual(res['cgst_inr'], 38.06)
        self.assertEqual(res['sgst_inr'], 38.06)

    def test_gst_breakdown_interstate_igst(self):
        """
        Inter-state transaction applies 18% IGST with CGST=0 and SGST=0.
        """
        res = calculate_inclusive_gst(49900, is_interstate=True)
        self.assertEqual(res['price_inclusive_paise'], 49900)
        self.assertEqual(res['base_taxable_paise'], 42288)
        self.assertEqual(res['total_gst_paise'], 7612)
        self.assertEqual(res['igst_paise'], 7612)
        self.assertEqual(res['cgst_paise'], 0)
        self.assertEqual(res['sgst_paise'], 0)
        self.assertTrue(res['is_interstate'])

    def test_zero_rounding_leakage_across_large_price_spectrum(self):
        """
        Mathematical Invariant Acceptance Test:
        Validates that for all integer price points from 1 to 10,000 paise (and large sample points up to 10,000,000 paise):
        1. base_taxable_paise + total_gst_paise == price_inclusive_paise
        2. cgst_paise + sgst_paise == total_gst_paise
        3. All amounts are non-negative.
        """
        test_prices = list(range(1, 10001)) + [
            49900, 99900, 149900, 199900, 249900, 499900, 999900, 10000000
        ]
        for price in test_prices:
            res = calculate_inclusive_gst(price)
            # Invariant 1: Zero leakage between base taxable and total GST
            self.assertEqual(
                res['base_taxable_paise'] + res['total_gst_paise'],
                price,
                f"GST leakage found for price {price} paise!"
            )
            # Invariant 2: Zero leakage between CGST + SGST and Total GST
            self.assertEqual(
                res['cgst_paise'] + res['sgst_paise'],
                res['total_gst_paise'],
                f"Tax split leakage found for price {price} paise!"
            )
            # Invariant 3: Non-negativity
            self.assertGreaterEqual(res['base_taxable_paise'], 0)
            self.assertGreaterEqual(res['total_gst_paise'], 0)
            self.assertGreaterEqual(res['cgst_paise'], 0)
            self.assertGreaterEqual(res['sgst_paise'], 0)


class OrderCreateAPITests(APITestCase):
    def setUp(self):
        self.now = timezone.now()
        self.student = User.objects.create_user(
            email="order_student@example.com",
            password="StrongPassword123!",
            role="STUDENT"
        )
        self.token = str(RefreshToken.for_user(self.student).access_token)

        self.board = Board.objects.create(name="CBSE Order", slug="cbse-order")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10-order")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="math-order")
        self.ch1 = Chapter.objects.create(subject=self.subject, chapter_number=1, title="Real Numbers", slug="real-numbers-order")
        self.ch2 = Chapter.objects.create(subject=self.subject, chapter_number=2, title="Polynomials", slug="polynomials-order")

        # Products
        self.prod_ch1 = Product.objects.create(
            title="Class 10 Math Chapter 1",
            slug="math-ch-1",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.ch1,
            is_active=True
        )
        Price.objects.create(product=self.prod_ch1, amount_paise=4900, is_current=True)

        self.prod_ch2 = Product.objects.create(
            title="Class 10 Math Chapter 2",
            slug="math-ch-2",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.ch2,
            is_active=True
        )
        Price.objects.create(product=self.prod_ch2, amount_paise=4900, is_current=True)

        self.prod_math_pack = Product.objects.create(
            title="Class 10 Math Subject Pack",
            slug="math-subject-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.subject,
            is_active=True
        )
        Price.objects.create(product=self.prod_math_pack, amount_paise=49900, is_current=True)

        self.coupon = Coupon.objects.create(
            code="ORDER50",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=5000,  # ₹50 = 5000 paise
            min_order_paise=5000,
            valid_from=self.now - timedelta(days=1),
            valid_until=self.now + timedelta(days=30),
            is_active=True
        )

    def test_order_create_requires_authentication(self):
        resp = self.client.post('/api/v1/orders/create/', {
            "items": [{"product_id": self.prod_ch1.id}]
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_order_create_rejects_empty_cart(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        resp = self.client.post('/api/v1/orders/create/', {"items": []}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cart is empty", str(resp.data))

    def test_order_create_success_pending_status_and_items(self):
        """
        Criteria:
        - Validates cart items, stores upgrade credits, coupon discount, and 18% GST split.
        - Order initialized with status PENDING.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        payload = {
            "items": [
                {"product_id": self.prod_ch1.id, "tampered_price": 10},
                {"product_id": self.prod_ch2.id, "tampered_price": 20}
            ]
        }

        resp = self.client.post('/api/v1/orders/create/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data

        self.assertEqual(data['status'], Order.STATUS_PENDING)
        self.assertTrue(data['order_number'].startswith("ORD-"))

        # 2 chapters at ₹49.00 each = 9800 paise gross
        self.assertEqual(data['gross_amount_paise'], 9800)
        self.assertEqual(data['upgrade_discount_paise'], 0)
        self.assertEqual(data['coupon_discount_paise'], 0)
        self.assertEqual(data['net_payable_paise'], 9800)

        # 18% GST split on 9800 paise:
        # Base taxable = round(9800 / 1.18) = 8305 paise
        # GST = 9800 - 8305 = 1495 paise
        self.assertEqual(data['taxable_base_paise'], 8305)
        self.assertEqual(data['gst_amount_paise'], 1495)
        self.assertEqual(data['taxable_base_paise'] + data['gst_amount_paise'], 9800)

        # Verify OrderItem records in database
        order_db = Order.objects.get(id=data['id'])
        self.assertEqual(order_db.status, Order.STATUS_PENDING)
        self.assertEqual(order_db.items.count(), 2)

        item_pids = set(order_db.items.values_list('product_id', flat=True))
        self.assertEqual(item_pids, {self.prod_ch1.id, self.prod_ch2.id})
        for it in order_db.items.all():
            self.assertEqual(it.unit_price_paise, 4900)
            self.assertEqual(it.net_price_paise, 4900)

    def test_order_create_with_upgrade_credit_and_coupon(self):
        """
        Student owns Math Ch 1 (4900 credit towards Math Subject Pack 49900).
        Cart has Math Subject Pack (49900 - 4900 = 45000 paise).
        Coupon ORDER50 deducts 5000 paise -> net payable = 40000 paise.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Grant ownership of Ch 1
        Entitlement.objects.create(
            user=self.student,
            product_type='CHAPTER',
            scope_id=self.ch1.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        payload = {
            "items": [{"product_id": self.prod_math_pack.id}],
            "coupon_code": "ORDER50"
        }

        resp = self.client.post('/api/v1/orders/create/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data

        self.assertEqual(data['gross_amount_paise'], 49900)
        self.assertEqual(data['upgrade_discount_paise'], 4900)
        self.assertEqual(data['coupon_code'], "ORDER50")
        self.assertEqual(data['coupon_discount_paise'], 5000)
        self.assertEqual(data['net_payable_paise'], 40000)  # 49900 - 4900 - 5000 = 40000

        # GST on 40000 paise:
        # round(40000 / 1.18) = 33898 paise base
        # GST = 40000 - 33898 = 6102 paise
        self.assertEqual(data['taxable_base_paise'], 33898)
        self.assertEqual(data['gst_amount_paise'], 6102)
        self.assertEqual(data['taxable_base_paise'] + data['gst_amount_paise'], 40000)

    def test_order_create_rejects_already_owned_item(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        Entitlement.objects.create(
            user=self.student,
            product_type='CHAPTER',
            scope_id=self.ch1.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        resp = self.client.post('/api/v1/orders/create/', {
            "items": [{"product_id": self.prod_ch1.id}]
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Owned", str(resp.data))

    def test_order_create_rejects_invalid_coupon(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        resp = self.client.post('/api/v1/orders/create/', {
            "items": [{"product_id": self.prod_ch1.id}],
            "coupon_code": "NONEXISTENT"
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid coupon code", str(resp.data))

    def test_order_list_and_detail_views(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create order
        create_resp = self.client.post('/api/v1/orders/create/', {
            "items": [{"product_id": self.prod_ch1.id}]
        }, format='json')
        order_id = create_resp.data['id']

        # List orders
        list_resp = self.client.get('/api/v1/orders/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 1)
        self.assertEqual(list_resp.data[0]['id'], order_id)

        # Detail order
        detail_resp = self.client.get(f'/api/v1/orders/{order_id}/')
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_resp.data['id'], order_id)
        self.assertEqual(len(detail_resp.data['items']), 1)





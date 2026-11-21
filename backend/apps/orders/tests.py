from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.products.models import Product, Price
from .models import Order, OrderItem, Coupon

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


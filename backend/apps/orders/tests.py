from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.products.models import Product, Price
from .models import Order, OrderItem

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

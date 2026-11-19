from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.orders.models import Order
from .models import Payment, WebhookEvent

User = get_user_model()


class PaymentAndWebhookModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student_pay@example.com",
            full_name="Payment Student",
            password="PayPassword@123"
        )
        self.order = Order.objects.create(
            user=self.user,
            order_number=Order.generate_order_number(),
            razorpay_order_id="order_pay_123",
            status=Order.STATUS_PENDING,
            net_payable_paise=49900
        )

    def test_payment_creation_and_attributes(self):
        payment = Payment.objects.create(
            order=self.order,
            razorpay_payment_id="pay_test_987654",
            razorpay_signature="sig_abc123xyz",
            payment_method="upi",
            amount_paise=49900,
            currency="INR",
            status=Payment.STATUS_CAPTURED
        )

        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.amount_paise, 49900)
        self.assertEqual(payment.status, Payment.STATUS_CAPTURED)
        self.assertIn("pay_test_987654", str(payment))
        self.assertIn("499.00", str(payment))

    def test_failed_payment_recording(self):
        failed_payment = Payment.objects.create(
            order=self.order,
            razorpay_payment_id="pay_fail_0001",
            payment_method="card",
            amount_paise=49900,
            status=Payment.STATUS_FAILED,
            error_code="BAD_REQUEST_ERROR",
            error_description="Payment was declined by bank"
        )
        self.assertEqual(failed_payment.status, Payment.STATUS_FAILED)
        self.assertEqual(failed_payment.error_code, "BAD_REQUEST_ERROR")

    def test_webhook_event_recording(self):
        event = WebhookEvent.objects.create(
            event_id="evt_test_12345",
            event_type="payment.captured",
            payload={"event": "payment.captured", "id": "evt_test_12345"},
            is_processed=False
        )
        self.assertFalse(event.is_processed)
        self.assertEqual(event.event_type, "payment.captured")
        self.assertIn("payment.captured", str(event))

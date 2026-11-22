import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.products.models import Product, Price
from apps.orders.models import Order
from apps.entitlements.models import Entitlement
from .models import Payment, WebhookEvent
from .services import (
    get_razorpay_client,
    create_razorpay_order,
    verify_razorpay_webhook_signature,
)

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


class RazorpayIntegrationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="razorpay_student@example.com",
            password="StrongPassword123!",
            role="STUDENT"
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.board = Board.objects.create(name="CBSE Razorpay", slug="cbse-rzp")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10-rzp")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="math-rzp")
        self.ch1 = Chapter.objects.create(subject=self.subject, chapter_number=1, title="Real Numbers", slug="real-numbers-rzp")

        self.prod_ch1 = Product.objects.create(
            title="Class 10 Math Chapter 1",
            slug="ch1-rzp-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.ch1,
            is_active=True
        )
        Price.objects.create(product=self.prod_ch1, amount_paise=4900, is_current=True)

        self.prod_pack = Product.objects.create(
            title="Class 10 Math Subject Pack",
            slug="math-pack-rzp",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.subject,
            is_active=True
        )
        Price.objects.create(product=self.prod_pack, amount_paise=4900, is_current=True)

    def test_get_razorpay_client_initialization(self):
        """
        Requirements: Read RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET from environment.
        """
        rzp_client = get_razorpay_client()
        self.assertIsNotNone(rzp_client)
        self.assertEqual(rzp_client.auth, (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    @patch('razorpay.Client')
    def test_razorpay_sdk_order_create_called_with_paise(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.order.create.return_value = {
            'id': 'order_rzp_live_test_123',
            'amount': 4900,
            'currency': 'INR',
            'receipt': 'ORD-MOCK-001',
            'status': 'created'
        }

        with patch.object(settings, 'RAZORPAY_KEY_ID', 'rzp_test_real_key_123'), \
             patch.object(settings, 'RAZORPAY_KEY_SECRET', 'real_secret_456'), \
             patch.object(settings, 'DEBUG', False):
            res = create_razorpay_order(
                amount_paise=4900,
                receipt='ORD-MOCK-001',
                currency='INR',
                notes={'test': '1'}
            )

        self.assertEqual(res['id'], 'order_rzp_live_test_123')
        mock_instance.order.create.assert_called_once_with(data={
            'amount': 4900,
            'currency': 'INR',
            'receipt': 'ORD-MOCK-001',
            'notes': {'test': '1'},
            'payment_capture': 1
        })

    def test_order_create_attaches_razorpay_order_id_and_returns_checkout_keys(self):
        """
        Acceptance Criteria:
        - Attaches razorpay_order_id to internal Order.
        - Returns order ID and key ID to frontend for Checkout modal.
        """
        payload = {
            "items": [{"product_id": self.prod_ch1.id}]
        }
        resp = self.client.post('/api/v1/orders/create/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data

        # Check frontend modal integration fields
        self.assertIn('razorpay_order_id', data)
        self.assertIsNotNone(data['razorpay_order_id'])
        self.assertTrue(data['razorpay_order_id'].startswith("order_"))
        self.assertIn('razorpay_key_id', data)
        self.assertEqual(data['razorpay_key_id'], settings.RAZORPAY_KEY_ID)
        self.assertEqual(data['amount_paise'], 4900)
        self.assertEqual(data['currency'], 'INR')
        self.assertEqual(data['status'], Order.STATUS_PENDING)

        # Verify internal database record
        order_db = Order.objects.get(id=data['id'])
        self.assertEqual(order_db.razorpay_order_id, data['razorpay_order_id'])
        self.assertEqual(order_db.net_payable_paise, 4900)
        self.assertEqual(order_db.status, Order.STATUS_PENDING)

    def test_zero_payable_order_marked_paid_without_razorpay(self):
        """
        US-PAY-01: Given an order where upgrade credit brings payable balance to ₹0,
        mark the order as PAID immediately without invoking Razorpay and grant entitlements directly.
        """
        # User owns Math Chapter 1 (worth 4900 paise)
        # Math Subject Pack is priced at 4900 paise
        # Upgrade credit = 4900 -> Net Payable = ₹0 (0 paise)
        Entitlement.objects.create(
            user=self.user,
            product_type='CHAPTER',
            scope_id=self.ch1.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        payload = {
            "items": [{"product_id": self.prod_pack.id}]
        }

        resp = self.client.post('/api/v1/orders/create/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data

        # ₹0 balance order
        self.assertEqual(data['net_payable_paise'], 0)
        self.assertEqual(data['status'], Order.STATUS_PAID)
        self.assertIsNone(data['razorpay_order_id'])

        # Entitlement for Subject Pack granted directly
        has_pack_entitlement = Entitlement.objects.filter(
            user=self.user,
            product_type='SUBJECT',
            scope_id=self.subject.id,
            status='ACTIVE'
        ).exists()
        self.assertTrue(has_pack_entitlement, "Subject pack entitlement should be granted immediately for ₹0 order")


class RazorpayWebhookAPITests(APITestCase):
    def setUp(self):
        self.webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', 'test_webhook_secret_key')
        self.sample_event_id = "evt_capture_12345"
        self.sample_payload = {
            "entity": "event",
            "account_id": "acc_test123",
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_payment_999",
                        "entity": "payment",
                        "amount": 4900,
                        "currency": "INR",
                        "status": "captured",
                        "order_id": "order_test_order_777",
                        "method": "upi",
                    }
                }
            },
            "created_at": 1700000000
        }
        self.sample_payload["id"] = self.sample_event_id

    def _generate_signature(self, raw_bytes: bytes) -> str:
        return hmac.new(
            self.webhook_secret.encode('utf-8'),
            raw_bytes,
            hashlib.sha256
        ).hexdigest()

    def test_webhook_missing_signature_rejected(self):
        raw_body = json.dumps(self.sample_payload).encode('utf-8')
        resp = self.client.post(
            '/api/v1/payments/webhook/',
            data=raw_body,
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Missing X-Razorpay-Signature", str(resp.data))

    def test_webhook_invalid_signature_rejected(self):
        raw_body = json.dumps(self.sample_payload).encode('utf-8')
        resp = self.client.post(
            '/api/v1/payments/webhook/',
            data=raw_body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE="tampered_invalid_signature_hex"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid webhook signature", str(resp.data))

    def test_webhook_valid_signature_persists_raw_event(self):
        """
        Acceptance Criteria:
        - Inspects X-Razorpay-Signature header.
        - Verifies signature against the unparsed, raw request body bytes using RAZORPAY_WEBHOOK_SECRET.
        - Saves raw event in webhook_events table before processing.
        """
        raw_body = json.dumps(self.sample_payload).encode('utf-8')
        valid_signature = self._generate_signature(raw_body)

        with patch.object(settings, 'RAZORPAY_WEBHOOK_SECRET', self.webhook_secret):
            resp = self.client.post(
                '/api/v1/payments/webhook/',
                data=raw_body,
                content_type='application/json',
                HTTP_X_RAZORPAY_SIGNATURE=valid_signature
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertEqual(data['status'], 'received')
        self.assertEqual(data['event_id'], self.sample_event_id)
        self.assertEqual(data['event_type'], 'payment.captured')

        # Verify event saved in webhook_events table with is_processed=False
        saved_event = WebhookEvent.objects.filter(event_id=self.sample_event_id).first()
        self.assertIsNotNone(saved_event)
        self.assertEqual(saved_event.event_type, 'payment.captured')
        self.assertFalse(saved_event.is_processed)
        self.assertEqual(saved_event.payload['payload']['payment']['entity']['id'], 'pay_test_payment_999')

    def test_webhook_idempotent_replay(self):
        """
        Duplicate delivery of the same webhook event ID does not duplicate records.
        """
        raw_body = json.dumps(self.sample_payload).encode('utf-8')
        valid_signature = self._generate_signature(raw_body)

        with patch.object(settings, 'RAZORPAY_WEBHOOK_SECRET', self.webhook_secret):
            resp1 = self.client.post(
                '/api/v1/payments/webhook/',
                data=raw_body,
                content_type='application/json',
                HTTP_X_RAZORPAY_SIGNATURE=valid_signature
            )
            self.assertEqual(resp1.status_code, status.HTTP_200_OK)

            # Replay same webhook
            resp2 = self.client.post(
                '/api/v1/payments/webhook/',
                data=raw_body,
                content_type='application/json',
                HTTP_X_RAZORPAY_SIGNATURE=valid_signature
            )
            self.assertEqual(resp2.status_code, status.HTTP_200_OK)
            self.assertEqual(resp2.data['status'], 'already_received')

        # Only 1 record in database
        self.assertEqual(WebhookEvent.objects.filter(event_id=self.sample_event_id).count(), 1)

    def test_webhook_malformed_json_rejected(self):
        raw_body = b"not_valid_json{"
        valid_signature = self._generate_signature(raw_body)

        with patch.object(settings, 'RAZORPAY_WEBHOOK_SECRET', self.webhook_secret):
            resp = self.client.post(
                '/api/v1/payments/webhook/',
                data=raw_body,
                content_type='application/json',
                HTTP_X_RAZORPAY_SIGNATURE=valid_signature
            )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Malformed JSON payload", str(resp.data))



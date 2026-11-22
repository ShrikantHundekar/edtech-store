import hmac
import hashlib
import json
import pytest
from django.conf import settings
from rest_framework.test import APIClient
from apps.payments.services import (
    verify_razorpay_checkout_signature,
    verify_razorpay_webhook_signature,
)
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.products.models import Product, Price
from apps.orders.models import Order, OrderItem
from apps.payments.models import WebhookEvent
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestRazorpayHMACSignatures:
    """
    Issue #51: Integration tests for Razorpay HMAC-SHA256 signature verification.
    Test Scenarios:
    - Valid HMAC-SHA256 signature returns True.
    - Tampered signature or wrong key secret returns False / HTTP 400.
    - Webhook signature verified against raw body bytes.
    """

    def test_checkout_signature_verification_valid_and_tampered(self, monkeypatch):
        """Checkout HMAC-SHA256 signature calculation and comparison using hmac.compare_digest."""
        secret = "secret_key_rzp_checkout_xyz"
        monkeypatch.setattr(settings, 'RAZORPAY_KEY_SECRET', secret)

        order_id = "order_rzp_test_12345"
        payment_id = "pay_rzp_test_67890"

        # Valid signature
        expected_msg = f"{order_id}|{payment_id}".encode('utf-8')
        valid_signature = hmac.new(secret.encode('utf-8'), expected_msg, hashlib.sha256).hexdigest()
        assert verify_razorpay_checkout_signature(order_id, payment_id, valid_signature) is True

        # Tampered signature
        tampered_signature = valid_signature[:-4] + "0000"
        assert verify_razorpay_checkout_signature(order_id, payment_id, tampered_signature) is False

        # Wrong secret
        monkeypatch.setattr(settings, 'RAZORPAY_KEY_SECRET', "wrong_secret_abc")
        assert verify_razorpay_checkout_signature(order_id, payment_id, valid_signature) is False

    def test_webhook_signature_verified_against_raw_body_bytes(self, monkeypatch):
        """Webhook signature must be verified strictly on raw bytes."""
        webhook_secret = "whsec_test_secret_999"
        monkeypatch.setattr(settings, 'RAZORPAY_WEBHOOK_SECRET', webhook_secret)

        payload = {"event": "payment.captured", "id": "evt_test_raw_bytes"}
        raw_bytes = json.dumps(payload).encode('utf-8')

        valid_sig = hmac.new(webhook_secret.encode('utf-8'), raw_bytes, hashlib.sha256).hexdigest()
        assert verify_razorpay_webhook_signature(raw_bytes, valid_sig) is True

        # Tampered payload bytes
        tampered_bytes = json.dumps({"event": "payment.captured", "id": "evt_tampered"}).encode('utf-8')
        assert verify_razorpay_webhook_signature(tampered_bytes, valid_sig) is False

        # Missing or empty signature
        assert verify_razorpay_webhook_signature(raw_bytes, "") is False

    def test_webhook_endpoint_rejects_tampered_signature_with_http_400(self, monkeypatch):
        """HTTP integration: Webhook view rejects invalid signatures with 400 Bad Request."""
        webhook_secret = "whsec_live_verify_123"
        monkeypatch.setattr(settings, 'RAZORPAY_WEBHOOK_SECRET', webhook_secret)

        client = APIClient()
        payload = {"event": "payment.captured", "id": "evt_http_tamper"}
        raw_body = json.dumps(payload).encode('utf-8')

        response = client.post(
            '/api/v1/payments/webhook/',
            data=raw_body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE="tampered_hex_value"
        )
        assert response.status_code == 400
        assert "Invalid webhook signature" in str(response.data)

    def test_checkout_verify_endpoint_rejects_tampered_signature_with_http_400(self, monkeypatch):
        """HTTP integration: Checkout verify endpoint rejects tampered signature with 400."""
        secret = "secret_checkout_verify_test"
        monkeypatch.setattr(settings, 'RAZORPAY_KEY_SECRET', secret)

        user = User.objects.create_user(email="verify_sig_user@example.com", password="Password123!")
        client = APIClient()
        client.force_authenticate(user=user)

        order = Order.objects.create(
            user=user,
            order_number=Order.generate_order_number(),
            razorpay_order_id="order_tamper_check_111",
            status=Order.STATUS_PENDING,
            net_payable_paise=4900
        )

        response = client.post(
            '/api/v1/payments/verify/',
            data={
                "razorpay_order_id": order.razorpay_order_id,
                "razorpay_payment_id": "pay_tamper_111",
                "razorpay_signature": "tampered_signature_value"
            },
            format='json'
        )
        assert response.status_code == 400
        assert "Invalid payment signature" in str(response.data)

import hmac
import hashlib
import json
import pytest
from django.conf import settings
from rest_framework.test import APIClient
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.products.models import Product, Price
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, WebhookEvent
from apps.entitlements.models import Entitlement
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestWebhookIdempotency:
    """
    Issue #52: Idempotency tests for duplicate webhook processing.
    Test Scenarios:
    - First delivery creates entitlements and sets status to PAID.
    - Second delivery returns HTTP 200 without creating duplicate rows or double revenue.
    """

    def test_duplicate_webhook_delivery_is_fully_idempotent(self, monkeypatch):
        webhook_secret = "whsec_idempotency_test_secret"
        monkeypatch.setattr(settings, 'RAZORPAY_WEBHOOK_SECRET', webhook_secret)

        user = User.objects.create_user(email="idempotent_user@example.com", password="Password123!")
        board = Board.objects.create(name="CBSE Idem", slug="cbse-idem")
        cls = ClassLevel.objects.create(board=board, name="Class 10", slug="c10-idem")
        subj = Subject.objects.create(academic_class=cls, name="History", slug="hist-idem")
        ch = Chapter.objects.create(subject=subj, chapter_number=1, title="Rise of Nationalism", slug="nationalism-idem")

        prod = Product.objects.create(
            title="Class 10 History Ch 1",
            slug="ch1-hist-notes-idem",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=ch
        )
        Price.objects.create(product=prod, amount_paise=4900, is_current=True)

        order = Order.objects.create(
            user=user,
            order_number=Order.generate_order_number(),
            razorpay_order_id="order_idem_test_999",
            status=Order.STATUS_PENDING,
            gross_amount_paise=4900,
            net_payable_paise=4900
        )
        OrderItem.objects.create(order=order, product=prod, unit_price_paise=4900, net_price_paise=4900)

        # Webhook payload
        payload = {
            "entity": "event",
            "event": "payment.captured",
            "id": "evt_capture_idempotent_1",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_idem_captured_999",
                        "amount": 4900,
                        "currency": "INR",
                        "status": "captured",
                        "order_id": order.razorpay_order_id,
                        "method": "upi",
                    }
                }
            }
        }
        raw_body = json.dumps(payload).encode('utf-8')
        sig = hmac.new(webhook_secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()

        client = APIClient()

        # Delivery 1: First delivery creates entitlements and transitions order to PAID
        resp1 = client.post(
            '/api/v1/payments/webhook/',
            data=raw_body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=sig
        )
        assert resp1.status_code == 200
        assert resp1.data['result']['status'] == 'fulfilled'

        order.refresh_from_db()
        assert order.status == Order.STATUS_PAID
        entitlements_count_1 = Entitlement.objects.filter(user=user, product_type='CHAPTER', scope_id=ch.id).count()
        assert entitlements_count_1 == 1

        payments_count_1 = Payment.objects.filter(order=order, status=Payment.STATUS_CAPTURED).count()
        assert payments_count_1 == 1

        # Delivery 2: Second duplicate delivery must return HTTP 200 without creating duplicate rows
        resp2 = client.post(
            '/api/v1/payments/webhook/',
            data=raw_body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=sig
        )
        assert resp2.status_code == 200
        assert resp2.data['status'] in ('already_received', 'processed')

        # Delivery 3: Delivery with new event_id but identical payment entity
        payload3 = dict(payload)
        payload3["id"] = "evt_capture_idempotent_2"
        raw_body3 = json.dumps(payload3).encode('utf-8')
        sig3 = hmac.new(webhook_secret.encode('utf-8'), raw_body3, hashlib.sha256).hexdigest()

        resp3 = client.post(
            '/api/v1/payments/webhook/',
            data=raw_body3,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=sig3
        )
        assert resp3.status_code == 200
        assert resp3.data['result']['status'] == 'already_paid'

        # Entitlements and payments counts must remain EXACTLY 1 (no duplicates, no double revenue)
        entitlements_count_2 = Entitlement.objects.filter(user=user, product_type='CHAPTER', scope_id=ch.id).count()
        assert entitlements_count_2 == 1

        payments_count_2 = Payment.objects.filter(order=order, status=Payment.STATUS_CAPTURED).count()
        assert payments_count_2 == 1

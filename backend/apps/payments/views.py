import json
import logging
import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import WebhookEvent
from .services import (
    verify_razorpay_webhook_signature,
    handle_payment_captured,
    handle_payment_failed,
    process_checkout_verification,
)

logger = logging.getLogger(__name__)


class RazorpayWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/
    Public webhook receiver for Razorpay asynchronous events.

    Security & Reliability:
    1. Inspects X-Razorpay-Signature HTTP header.
    2. Cryptographically validates signature against raw, unparsed request body bytes using RAZORPAY_WEBHOOK_SECRET.
    3. Rejects invalid or missing signatures with HTTP 400 Bad Request.
    4. Persists the raw event payload into the webhook_events table before processing for audit trail & replay protection.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        signature = request.headers.get('X-Razorpay-Signature') or request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
        if not signature:
            logger.warning("Razorpay webhook received without X-Razorpay-Signature header.")
            return Response(
                {"error": "Missing X-Razorpay-Signature header."},
                status=status.HTTP_400_BAD_REQUEST
            )

        raw_body = request.body
        if not verify_razorpay_webhook_signature(raw_body, signature):
            logger.warning("Razorpay webhook signature verification failed.")
            return Response(
                {"error": "Invalid webhook signature."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse webhook JSON body: {e}")
            return Response(
                {"error": "Malformed JSON payload."},
                status=status.HTTP_400_BAD_REQUEST
            )

        event_id = payload.get('id') or payload.get('event_id')
        if not event_id:
            event_id = f"evt_{hashlib.sha256(raw_body).hexdigest()[:16]}"

        event_type = payload.get('event', 'unknown')

        # Persist raw event to webhook_events table before processing
        webhook_event, created = WebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                'event_type': event_type,
                'payload': payload,
                'is_processed': False
            }
        )

        if not created:
            logger.info(f"Duplicate webhook event {event_id} already recorded.")
            return Response(
                {
                    "status": "already_received",
                    "event_id": event_id,
                    "event_type": event_type,
                    "is_processed": webhook_event.is_processed
                },
                status=status.HTTP_200_OK
            )

        logger.info(f"Successfully recorded webhook event {event_id} ({event_type})")

        # Process payment.captured event
        if event_type == 'payment.captured':
            result = handle_payment_captured(payload, webhook_event=webhook_event)
            if not result['success']:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {
                    "status": "processed",
                    "event_id": event_id,
                    "event_type": event_type,
                    "result": result
                },
                status=status.HTTP_200_OK
            )

        elif event_type == 'payment.failed':
            result = handle_payment_failed(payload, webhook_event=webhook_event)
            if not result['success']:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {
                    "status": "processed",
                    "event_id": event_id,
                    "event_type": event_type,
                    "result": result
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "status": "received",
                "event_id": event_id,
                "event_type": event_type,
            },
            status=status.HTTP_200_OK
        )


class RazorpayPaymentVerifyView(APIView):
    """
    POST /api/v1/payments/verify/
    Frontend checkout callback verification endpoint.
    Verifies HMAC-SHA256 signature and fulfills order with dual-path idempotency.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response(
                {"error": "Missing required fields: razorpay_order_id, razorpay_payment_id, razorpay_signature."},
                status=status.HTTP_400_BAD_REQUEST
            )

        result = process_checkout_verification(
            user=request.user,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature
        )

        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class RazorpayPaymentSimulateView(APIView):
    """
    POST /api/v1/payments/simulate/
    Available for testing/dev environments to simulate realistic Razorpay checkout callbacks (UPI & Card).
    Returns cryptographically valid HMAC-SHA256 signature for testing verify endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        import uuid
        import hmac
        from django.conf import settings
        from django.shortcuts import get_object_or_404
        from apps.orders.models import Order

        razorpay_order_id = request.data.get('razorpay_order_id')
        method = request.data.get('method', 'upi')
        should_fail = request.data.get('fail', False)

        if not razorpay_order_id:
            return Response(
                {"error": "Missing razorpay_order_id."},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = get_object_or_404(Order, razorpay_order_id=razorpay_order_id)
        if order.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "Permission denied for this order."},
                status=status.HTTP_403_FORBIDDEN
            )

        if should_fail:
            return Response(
                {
                    "success": False,
                    "error": "Payment was declined by the bank (Simulated Failure).",
                    "code": "PAYMENT_DECLINED"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_id = f"pay_sim_{method}_{uuid.uuid4().hex[:10]}"
        key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
        message = f"{razorpay_order_id}|{payment_id}".encode('utf-8')
        signature = hmac.new(key_secret.encode('utf-8'), message, hashlib.sha256).hexdigest()

        return Response(
            {
                "success": True,
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
                "method": method,
            },
            status=status.HTTP_200_OK
        )



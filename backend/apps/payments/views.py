import json
import logging
import hashlib
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import WebhookEvent
from .services import verify_razorpay_webhook_signature

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

        return Response(
            {
                "status": "received",
                "event_id": event_id,
                "event_type": event_type,
            },
            status=status.HTTP_200_OK
        )

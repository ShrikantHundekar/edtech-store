import hmac
import hashlib
import uuid
import logging
import razorpay
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_razorpay_client():
    """
    Initializes and returns the official Razorpay client with credentials from settings.
    """
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    return razorpay.Client(auth=(key_id, key_secret))


def create_razorpay_order(amount_paise: int, receipt: str, currency: str = 'INR', notes: dict = None) -> dict:
    """
    Creates an order in Razorpay for checkout.
    Uses official Razorpay Python SDK: client.order.create().
    
    If running with dummy placeholder credentials (e.g. during local offline dev or unit testing),
    generates a realistic simulated Razorpay order to prevent network blocks while preserving
    exact order schema structure.
    """
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

    # Check for placeholder / dummy credentials or test mock mode
    is_placeholder = (
        not key_id or
        not key_secret or
        'placeholder' in key_id.lower() or
        getattr(settings, 'RAZORPAY_MOCK_ORDERS', False)
    )

    if is_placeholder:
        mock_order_id = f"order_{uuid.uuid4().hex[:14]}"
        logger.info(f"Using simulated Razorpay Order: {mock_order_id} for amount {amount_paise} paise")
        return {
            'id': mock_order_id,
            'entity': 'order',
            'amount': amount_paise,
            'amount_paid': 0,
            'amount_due': amount_paise,
            'currency': currency,
            'receipt': receipt,
            'status': 'created',
            'attempts': 0,
            'notes': notes or {},
            'created_at': int(timezone.now().timestamp()),
        }

    client = get_razorpay_client()
    order_data = {
        'amount': amount_paise,
        'currency': currency,
        'receipt': receipt,
        'notes': notes or {},
        'payment_capture': 1,
    }

    try:
        razorpay_order = client.order.create(data=order_data)
        return razorpay_order
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        # If API call fails due to invalid test key or offline connection in dev, fallback gracefully
        if settings.DEBUG:
            mock_order_id = f"order_sim_{uuid.uuid4().hex[:12]}"
            logger.warning(f"Fallback to simulated Razorpay order ID in DEBUG mode: {mock_order_id}")
            return {
                'id': mock_order_id,
                'entity': 'order',
                'amount': amount_paise,
                'currency': currency,
                'receipt': receipt,
                'status': 'created',
                'notes': notes or {},
            }
        raise


def verify_razorpay_checkout_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Cryptographic verification of Razorpay checkout callback signature.
    Expected signature = HMAC-SHA256(order_id + "|" + payment_id, secret=RAZORPAY_KEY_SECRET)
    """
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    if not key_secret:
        return False

    message = f"{order_id}|{payment_id}".encode('utf-8')
    generated = hmac.new(
        key_secret.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(generated, signature)


def verify_razorpay_webhook_signature(raw_body: bytes, received_signature: str) -> bool:
    """
    Cryptographic verification of Razorpay asynchronous webhook signature.
    Validated strictly against raw, unparsed request body bytes.
    Expected signature = HMAC-SHA256(raw_body, secret=RAZORPAY_WEBHOOK_SECRET)
    """
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    if not webhook_secret or not received_signature:
        return False

    generated = hmac.new(
        webhook_secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(generated, received_signature)


def fulfill_order_payment(
    order,
    payment_id: str,
    amount_paise: int,
    currency: str = 'INR',
    method: str = '',
    webhook_event=None
) -> dict:
    """
    Central, thread-safe, dual-path fulfillment engine.
    Ensures that whether called by the frontend checkout callback or the asynchronous webhook
    (or both concurrently), the order transition and entitlement provisioning happen exactly once.
    """
    from django.db import transaction
    from django.utils import timezone
    from apps.orders.models import Order
    from apps.payments.models import Payment
    from apps.entitlements.services import provision_order_entitlements

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().filter(id=order.id).first()
        if not locked_order:
            return {
                "success": False,
                "error": "Order not found."
            }

        # Dual-Path Idempotency: if already PAID, return immediately without re-provisioning
        if locked_order.status == Order.STATUS_PAID:
            logger.info(f"Dual-path idempotency: Order {locked_order.order_number} is already PAID. Skipping duplicate fulfillment.")
            if webhook_event:
                webhook_event.is_processed = True
                webhook_event.processed_at = timezone.now()
                webhook_event.save(update_fields=['is_processed', 'processed_at'])
            return {
                "success": True,
                "status": "already_paid",
                "order_id": locked_order.id,
                "order_number": locked_order.order_number,
                "message": "Order is already fulfilled."
            }

        # Amount reconciliation: verify amount_paid == locked_order.net_payable_paise
        if amount_paise is not None and int(amount_paise) != locked_order.net_payable_paise:
            logger.critical(
                f"SECURITY ALERT: Amount reconciliation mismatch! "
                f"Order {locked_order.order_number}: expected {locked_order.net_payable_paise} paise, but received {amount_paise} paise!"
            )
            Payment.objects.update_or_create(
                razorpay_payment_id=payment_id or f"failed_{uuid.uuid4().hex[:12]}",
                defaults={
                    'order': locked_order,
                    'amount_paise': int(amount_paise) if amount_paise is not None else 0,
                    'currency': currency,
                    'payment_method': method,
                    'status': Payment.STATUS_FAILED,
                    'error_code': 'AMOUNT_MISMATCH',
                    'error_description': f"Expected {locked_order.net_payable_paise} paise, but received {amount_paise} paise.",
                }
            )
            return {
                "success": False,
                "error": f"Amount reconciliation mismatch: expected {locked_order.net_payable_paise} paise, got {amount_paise} paise."
            }

        # Record or update Payment record
        Payment.objects.update_or_create(
            razorpay_payment_id=payment_id,
            defaults={
                'order': locked_order,
                'amount_paise': int(amount_paise) if amount_paise is not None else locked_order.net_payable_paise,
                'currency': currency,
                'payment_method': method,
                'status': Payment.STATUS_CAPTURED,
            }
        )

        # Atomically transition order status to PAID
        locked_order.status = Order.STATUS_PAID
        locked_order.save(update_fields=['status', 'updated_at'])

        # Provision student entitlements
        entitlements = provision_order_entitlements(locked_order)
        logger.info(f"Granted {len(entitlements)} entitlements for Order {locked_order.order_number} to {locked_order.user.email}")

        # Mark webhook event as processed if provided
        if webhook_event:
            webhook_event.is_processed = True
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=['is_processed', 'processed_at'])

        return {
            "success": True,
            "status": "fulfilled",
            "order_id": locked_order.id,
            "order_number": locked_order.order_number,
            "entitlements_count": len(entitlements),
            "message": "Payment verified and order fulfilled successfully."
        }


def handle_payment_captured(payload: dict, webhook_event=None) -> dict:
    """
    Fulfills order upon receiving payment.captured webhook:
    1. Extracts payment entity and order ID.
    2. Performs amount reconciliation and atomic row lock via fulfill_order_payment.
    3. Handles dual-path idempotency: if order already PAID, skips duplicate fulfillment.
    4. Transitions order.status = 'PAID'.
    5. Records Payment record with status 'CAPTURED'.
    6. Provisions student entitlements.
    7. Marks WebhookEvent as processed.
    """
    from apps.orders.models import Order

    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    if not payment_entity:
        payment_entity = payload.get('payment', {})

    payment_id = payment_entity.get('id')
    razorpay_order_id = payment_entity.get('order_id')
    amount_paid = payment_entity.get('amount')
    currency = payment_entity.get('currency', 'INR')
    method = payment_entity.get('method', '')

    notes = payment_entity.get('notes', {}) or {}
    order_number = notes.get('order_number')
    order_id_fallback = notes.get('order_id')

    order = None
    if razorpay_order_id:
        order = Order.objects.filter(razorpay_order_id=razorpay_order_id).first()
    if not order and order_number:
        order = Order.objects.filter(order_number=order_number).first()
    if not order and order_id_fallback:
        order = Order.objects.filter(id=order_id_fallback).first()

    if not order:
        logger.error(f"Order not found for payment.captured: rzp_order={razorpay_order_id}, payment_id={payment_id}")
        return {
            "success": False,
            "error": f"No order found matching Razorpay order ID '{razorpay_order_id}'."
        }

    return fulfill_order_payment(
        order=order,
        payment_id=payment_id,
        amount_paise=amount_paid,
        currency=currency,
        method=method,
        webhook_event=webhook_event
    )


def process_checkout_verification(user, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> dict:
    """
    Dual-path checkout callback verification:
    1. Cryptographically validates checkout signature (HMAC-SHA256).
    2. Uses select_for_update row locking to ensure idempotency.
    3. If order is already PAID, returns HTTP 200 immediately.
    4. Otherwise, fulfills order and provisions entitlements exactly once.
    """
    from django.db import transaction
    from apps.orders.models import Order

    if not verify_razorpay_checkout_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        logger.warning(f"Signature mismatch during checkout verification for order {razorpay_order_id}")
        return {
            "success": False,
            "error": "Invalid payment signature."
        }

    with transaction.atomic():
        order = Order.objects.select_for_update().filter(razorpay_order_id=razorpay_order_id).first()
        if not order:
            logger.error(f"Order not found for checkout verification: {razorpay_order_id}")
            return {
                "success": False,
                "error": f"Order not found for Razorpay order ID '{razorpay_order_id}'."
            }

        # Check user ownership (allow staff/admin or order owner)
        if user and not getattr(user, 'is_staff', False) and order.user != user:
            return {
                "success": False,
                "error": "You do not have permission to verify this order."
            }

        return fulfill_order_payment(
            order=order,
            payment_id=razorpay_payment_id,
            amount_paise=order.net_payable_paise,
            currency='INR',
            method='razorpay_checkout'
        )


def handle_payment_failed(payload: dict, webhook_event=None) -> dict:
    """
    Handles payment.failed webhook event:
    1. Extracts failure code, description, and order reference.
    2. Records failed attempt in the payments table with error details.
    3. If order is in PENDING status, transitions order.status = 'FAILED'.
    4. Ensures zero entitlements are granted to the user.
    5. Marks webhook_event as processed.
    """
    from django.db import transaction
    from django.utils import timezone
    from apps.orders.models import Order
    from apps.payments.models import Payment

    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    if not payment_entity:
        payment_entity = payload.get('payment', {})

    payment_id = payment_entity.get('id')
    razorpay_order_id = payment_entity.get('order_id')
    amount = payment_entity.get('amount') or 0
    currency = payment_entity.get('currency', 'INR')
    method = payment_entity.get('method', '')
    error_code = payment_entity.get('error_code', 'PAYMENT_FAILED')
    error_description = payment_entity.get('error_description', 'Payment failed or was declined.')

    notes = payment_entity.get('notes', {}) or {}
    order_number = notes.get('order_number')
    order_id_fallback = notes.get('order_id')

    with transaction.atomic():
        order = None
        if razorpay_order_id:
            order = Order.objects.select_for_update().filter(razorpay_order_id=razorpay_order_id).first()
        if not order and order_number:
            order = Order.objects.select_for_update().filter(order_number=order_number).first()
        if not order and order_id_fallback:
            order = Order.objects.select_for_update().filter(id=order_id_fallback).first()

        if not order:
            logger.error(f"Order not found for payment.failed: rzp_order={razorpay_order_id}, payment_id={payment_id}")
            return {
                "success": False,
                "error": f"No order found matching Razorpay order ID '{razorpay_order_id}'."
            }

        # Record failed transaction in payments table
        Payment.objects.update_or_create(
            razorpay_payment_id=payment_id or f"failed_{uuid.uuid4().hex[:12]}",
            defaults={
                'order': order,
                'amount_paise': int(amount),
                'currency': currency,
                'payment_method': method,
                'status': Payment.STATUS_FAILED,
                'error_code': error_code,
                'error_description': error_description,
            }
        )

        # Only transition to FAILED if order is not already PAID
        if order.status == Order.STATUS_PENDING:
            order.status = Order.STATUS_FAILED
            order.save(update_fields=['status', 'updated_at'])
            logger.info(f"Order {order.order_number} marked as FAILED due to {error_code}: {error_description}")

        # Mark webhook event as processed
        if webhook_event:
            webhook_event.is_processed = True
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=['is_processed', 'processed_at'])

        return {
            "success": True,
            "status": "failed_recorded",
            "order_id": order.id,
            "order_number": order.order_number,
            "order_status": order.status,
            "error_code": error_code,
            "error_description": error_description,
        }



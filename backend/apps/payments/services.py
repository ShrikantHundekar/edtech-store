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

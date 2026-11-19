# 07. Testing Suite & Security Checklist

This document details the automated testing requirements, test scenarios, and security hardening checklist mandated by the assessment.

---

## 🧪 1. Automated Testing Requirements

All automated tests should be authored using **Pytest** (`pytest-django`). The test suite must pass completely with zero regressions.

### A. Mandatory Assessment Tests

| # | Test Case | Target Logic | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **T1** | **Price Calculation Engine** | Upgrade credit calculation, percentage/flat coupons, and 18% inclusive GST split. | Net price accurately deducts prior chapter payments (floored at 0); GST equals `Price - (Price / 1.18)`. |
| **T2** | **Payment Signature Verification** | Backend signature verification via HMAC-SHA256 (`order_id\|payment_id` with `secret`). | Returns `True` for authentic signature; returns `False` / HTTP 400 for tampered signature or mismatched secret. |
| **T3** | **Idempotent Webhook Processing** | Ingesting the identical `payment.captured` webhook payload twice. | First request grants access; second request acknowledges HTTP 200 without creating duplicate entitlements or duplicate revenue. |
| **T4** | **Locked Content Access Check** | Unauthenticated or un-entitled student attempting `GET /api/v1/materials/{id}/stream/`. | Server returns **HTTP 403 Forbidden** (not 200 or 404). Access is rejected at the API level, not merely hidden in UI. |

---

### B. Additional Recommended Test Coverage

| # | Test Scenario | Expected Behavior |
| :--- | :--- | :--- |
| **T5** | **Role-Based API Enforcement** | A user with role `STUDENT` attempting `POST /api/v1/admin/boards/` receives **HTTP 403 Forbidden**. |
| **T6** | **Failed Payment Flow** | A `payment.failed` event transitions order to `FAILED` and provisions **zero** entitlements. |
| **T7** | **Tampered Payment Amount** | Payment captured with an amount less than `order.net_payable_paise` throws an error and denies access. |
| **T8** | **Expired Pass Revocation** | A time-bound pass whose `valid_until` is in the past fails access checks for class materials. |
| **T9** | **Early Pass Renewal Stacking** | A user with 10 days left on a 30-day pass purchases a 30-day renewal; new `valid_until` equals `old_valid_until + 30 days` (40 days total). |
| **T10** | **Coupon Caps & Expiry** | Applying an expired coupon or a coupon that has reached `usage_limit` is rejected with an informative error. |

---

### C. Sample Pytest Implementations

#### 1. Price Engine & GST Test (`test_pricing.py`):
```python
import pytest
from apps.products.services import calculate_cart_breakdown

def test_subject_pack_upgrade_credit_and_gst():
    # User owns Chapter 1 (₹49 paid)
    # Subject Pack full price is ₹499 (49900 paise)
    prior_paid_paise = 4900
    subject_pack_paise = 49900
    
    breakdown = calculate_cart_breakdown(
        items=[{'price_paise': subject_pack_paise, 'upgrade_credit_paise': prior_paid_paise}],
        coupon=None
    )
    
    # Net payable = 49900 - 4900 = 45000 paise (₹450.00)
    assert breakdown['net_payable_paise'] == 45000
    
    # Base Taxable = 45000 / 1.18 = 38136 paise
    assert breakdown['taxable_base_paise'] == round(45000 / 1.18)
    
    # GST = 45000 - 38136 = 6864 paise
    assert breakdown['gst_amount_paise'] == 45000 - round(45000 / 1.18)
```

#### 2. Signature Verification Test (`test_signatures.py`):
```python
import hmac
import hashlib
from apps.payments.services import verify_razorpay_checkout_signature

def test_valid_and_tampered_razorpay_signature():
    order_id = "order_N123456789"
    payment_id = "pay_P987654321"
    secret = "test_secret_key_123"
    
    # Valid signature
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    
    assert verify_razorpay_checkout_signature(order_id, payment_id, valid_sig, secret) is True
    
    # Tampered signature
    tampered_sig = valid_sig[:-4] + "ffff"
    assert verify_razorpay_checkout_signature(order_id, payment_id, tampered_sig, secret) is False
```

#### 3. Idempotent Entitlement Grant Test (`test_idempotency.py`):
```python
from apps.orders.services import fulfill_order
from apps.entitlements.models import Entitlement

def test_duplicate_webhook_fulfillment_is_idempotent(db, paid_order):
    # First fulfillment
    fulfill_order(paid_order.id)
    first_count = Entitlement.objects.filter(order=paid_order).count()
    assert first_count > 0
    
    # Duplicate fulfillment (second webhook delivery)
    fulfill_order(paid_order.id)
    second_count = Entitlement.objects.filter(order=paid_order).count()
    assert second_count == first_count  # No duplicate rows created
```

---

## 🔒 2. Comprehensive Security Checklist

Before deploying or recording the demonstration, verify each security control:

- [ ] **Password Security**: Passwords hashed using Argon2 or bcrypt with appropriate salt rounds. Plaintext passwords never stored or logged.
- [ ] **Token Security**: JWT tokens signed with strong random secret; access tokens short-lived (e.g. 15–30 mins); refresh tokens rotatable.
- [ ] **Input Validation**: All request bodies validated against DRF serializers before database or payment calls.
- [ ] **Rate Limiting**: Authentication (`/api/v1/auth/login/`) and order initiation endpoints rate-limited via DRF Throttling to prevent credential stuffing.
- [ ] **Secrets Segregation**: `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET` reside solely in backend `.env` files; never bundled into React code or committed to Git.
- [ ] **Server-Side Cryptography**: Checkout signatures verified with HMAC-SHA256; webhooks verified against raw payload bytes before JSON deserialization.
- [ ] **Financial Verification**: Payment amount paid verified strictly against `order.net_payable_paise` before entitlement issuance.
- [ ] **Protected Media Server**: PDF notes stored outside the public directory; file streaming only occurs after confirming the student's active entitlement.
- [ ] **Role-Based Authorization**: Administrative routes enforce `IsAdminUser` permission; non-admin users always receive HTTP 403 Forbidden.
- [ ] **CORS Hardening**: Cross-Origin Resource Sharing (CORS) restricted to the local frontend origin (e.g., `http://localhost:5173`).

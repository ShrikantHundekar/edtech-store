# 05. Razorpay Integration & Entitlement Engine

This document defines the payment integration architecture, cryptographic verification protocols, dual-path idempotency model, and the server-side entitlement engine.

---

## 💳 1. Razorpay Test Mode Architecture

All transactions use **Razorpay Test Mode**. Test credentials (`rzp_test_*`) and webhook secrets are loaded strictly from environment variables.

```
┌─────────────────┐      1. Create Order       ┌──────────────────┐
│  React Frontend ├───────────────────────────►│  Django Backend  │
│                 │◄───────────────────────────┤ (Generates Order)│
│                 │   2. razorpay_order_id     └─────────┬────────┘
│                 │                                      │
│                 │ 3. Open Checkout                     │ Razorpay API
│                 │                                      ▼
│  Razorpay Modal │                             ┌──────────────────┐
│  (UPI / Card)   ├────────────────────────────►│  Razorpay Server │
│                 │◄───────────────────────────┤                  │
└────────┬────────┘      4. Payment Success     └────────┬─────────┘
         │                                               │
         │ 5. Returns:                                   │ 6. Asynchronous Webhook:
         │    - razorpay_payment_id                      │    payment.captured
         │    - razorpay_order_id                        │    (X-Razorpay-Signature)
         │    - razorpay_signature                       │
         ▼                                               ▼
┌──────────────────────────────────────────────────────────────────┐
│               Idempotent Access Provisioning Service             │
│   (Grants Entitlement EXACTLY ONCE regardless of which arrives) │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔐 2. Cryptographic Payment Verification

Payment access must **never** be granted simply because a frontend callback succeeded. The backend must independently verify cryptographic proof.

### A. Frontend Checkout Modal Verification
Upon successful payment inside the checkout modal, Razorpay delivers three payload fields to the frontend:
1. `razorpay_order_id`
2. `razorpay_payment_id`
3. `razorpay_signature`

The frontend posts this payload to `/api/v1/payments/verify/`. The backend verifies the signature:
$$\text{Expected Signature} = \text{HMAC-SHA256}(\text{data}=\text{order\_id} + \text{"\|"} + \text{payment\_id}, \; \text{key}=\text{RAZORPAY\_KEY\_SECRET})$$

```python
import hmac
import hashlib

def verify_razorpay_checkout_signature(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    message = f"{order_id}|{payment_id}".encode("utf-8")
    generated_signature = hmac.new(
        secret.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, signature)
```

---

### B. Webhook Verification
Razorpay emits asynchronous webhooks to `/api/v1/payments/webhook/`.
1. The backend inspects the `X-Razorpay-Signature` HTTP header.
2. The signature **must** be validated against the **raw, unparsed request body bytes**.
3. If valid, the webhook body is parsed to inspect `event`:
   - `payment.captured`: Triggers order fulfillment.
   - `payment.failed`: Records failure in `payments` table and updates `orders.status = 'FAILED'`.

```python
def verify_razorpay_webhook_signature(raw_body: bytes, received_signature: str, webhook_secret: str) -> bool:
    generated_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(generated_signature, received_signature)
```

---

## ⚡ 3. Dual-Path Idempotency & Race Condition Handling

### The Dual-Path Problem:
Because network conditions vary:
- Path A: The frontend user finishes checkout and calls `/api/v1/payments/verify/`.
- Path B: Razorpay triggers the `payment.captured` webhook.
- **Race Condition**: Path A and Path B may arrive in **any order**, simultaneously, or one may fail entirely (e.g., student closes browser tab before callback).

### Idempotency Execution Rules:
1. **Database Lock & Transaction**:
   - Wrap entitlement creation in an atomic database transaction (`transaction.atomic()` with `select_for_update()`).
2. **Order Amount Verification**:
   - Verify that `amount_paid == order.net_payable_paise`. If amounts mismatch, flag for fraud and deny access.
3. **Exactly-Once Entitlement Grant**:
   - If `order.status == 'PAID'`, the order has already been processed. Return HTTP 200 immediately without duplicating entitlements or double-counting revenue.
   - If `order.status == 'PENDING'`, atomically mark `order.status = 'PAID'` and provision `entitlements`.

---

## 🎓 4. Entitlement Engine Logic

When an order transitions to `PAID`, entitlements are issued based on `order_items`:

| Product Type | Entitlement Scope | `access_type` | `valid_until` Calculation |
| :--- | :--- | :--- | :--- |
| **Chapter Notes** | Chapter ID | `LIFETIME` | `NULL` |
| **Subject Pack** | Subject ID | `LIFETIME` | `NULL` |
| **Monthly Pass** | Class ID | `TIME_BOUND` | If no active pass: `now() + 30 days`<br>If active pass exists: `old_expiry + 30 days` |
| **Annual Pass** | Class ID | `TIME_BOUND` | If no active pass: `now() + 365 days`<br>If active pass exists: `old_expiry + 365 days` |
| **Custom Bundle** | Multiple Chapter/Subject IDs | `LIFETIME` | `NULL` |
| **Free Sample** | Chapter ID | `LIFETIME` | `NULL` |

### Pass Renewal Stacking:
```python
def calculate_pass_validity(user_id: int, class_id: int, duration_days: int):
    active_pass = Entitlement.objects.filter(
        user_id=user_id,
        product_type='CLASS_PASS',
        scope_id=class_id,
        status='ACTIVE',
        valid_until__gt=timezone.now()
    ).order_by('-valid_until').first()

    base_time = active_pass.valid_until if active_pass else timezone.now()
    return base_time + datetime.timedelta(days=duration_days)
```

---

## 🔒 5. Server-Side Protected Content Delivery

1. **Non-Guessable Storage**:
   - PDF files must **never** be placed in a public web root or assigned predictable URLs (e.g. `/media/chapter1.pdf`).
2. **Authorization Gate**:
   - Students request files via `GET /api/v1/materials/{id}/stream/`.
   - The backend executes an authorization check against active entitlements:
     ```python
     def has_access_to_material(user, material):
         chapter = material.chapter
         if chapter.is_free_sample:
             return True
         return Entitlement.objects.filter(
             user=user,
             status='ACTIVE',
             # Check Chapter ownership OR Subject Pack OR active Class Pass
         ).filter(
             Q(product_type='CHAPTER', scope_id=chapter.id) |
             Q(product_type='SUBJECT', scope_id=chapter.subject_id) |
             Q(product_type='CLASS_PASS', scope_id=chapter.subject.class_id, valid_until__gt=timezone.now())
         ).exists()
     ```
3. **Streaming / Delivery**:
   - If unauthorized: Return **HTTP 403 Forbidden**.
   - If authorized: Stream binary data via Django's `FileResponse` with `Content-Type: application/pdf` or generate a 5-minute expiring signed URL.

---

## 🧪 6. Razorpay Test Credentials & Simulation Scenarios

| Test Target | Identifier / Details | Expected Outcome |
| :--- | :--- | :--- |
| **UPI Success** | VPA: `success@razorpay` | Order transitions to `PAID`, entitlements granted immediately. |
| **UPI Failure** | VPA: `failure@razorpay` | Order remains `FAILED`/`PENDING`, zero entitlements granted, student can retry. |
| **Test Cards** | Razorpay published standard test cards (e.g. standard mastercard/visa test numbers) | Standard card payment success simulation. |
| **Webhook Tunneling**| **ngrok** (`ngrok http 8000`) or **Cloudflare Tunnel** | Forward webhook events from Razorpay dashboard to local machine. |

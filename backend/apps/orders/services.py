from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .gst import calculate_gst_breakdown
from .models import Coupon


def validate_and_apply_coupon(code: str, subtotal_paise: int, user=None) -> dict:
    """
    Validates promotional coupon code against:
    - Existence
    - Active status
    - Date validity window (valid_from <= now <= valid_until)
    - Usage limits (times_used < usage_limit)
    - Minimum cart/order value requirement (subtotal_paise >= min_order_paise)

    Returns:
        dict: {
            "valid": bool,
            "error": str or None,
            "coupon": dict or None,
            "discount_paise": int,
            "discount_inr": float,
            "subtotal_paise": int,
            "subtotal_inr": float,
            "net_payable_paise": int,
            "net_payable_inr": float,
            "gst_breakdown": dict
        }
    """
    if not code or not code.strip():
        return {
            "valid": False,
            "error": "Coupon code is required.",
            "coupon": None,
            "discount_paise": 0,
            "discount_inr": 0.0,
            "subtotal_paise": subtotal_paise,
            "subtotal_inr": subtotal_paise / 100.0,
            "net_payable_paise": subtotal_paise,
            "net_payable_inr": subtotal_paise / 100.0,
            "gst_breakdown": calculate_gst_breakdown(subtotal_paise),
        }

    clean_code = code.strip()
    coupon = Coupon.objects.filter(code__iexact=clean_code).first()
    if not coupon:
        return {
            "valid": False,
            "error": f"Invalid coupon code '{clean_code}'.",
            "coupon": None,
            "discount_paise": 0,
            "discount_inr": 0.0,
            "subtotal_paise": subtotal_paise,
            "subtotal_inr": subtotal_paise / 100.0,
            "net_payable_paise": subtotal_paise,
            "net_payable_inr": subtotal_paise / 100.0,
            "gst_breakdown": calculate_gst_breakdown(subtotal_paise),
        }

    is_valid, error_msg, discount_paise = coupon.validate_for_cart(subtotal_paise)
    if not is_valid:
        return {
            "valid": False,
            "error": error_msg,
            "coupon": {
                "id": coupon.id,
                "code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": coupon.discount_value,
                "min_order_paise": coupon.min_order_paise,
                "max_discount_paise": coupon.max_discount_paise,
            },
            "discount_paise": 0,
            "discount_inr": 0.0,
            "subtotal_paise": subtotal_paise,
            "subtotal_inr": subtotal_paise / 100.0,
            "net_payable_paise": subtotal_paise,
            "net_payable_inr": subtotal_paise / 100.0,
            "gst_breakdown": calculate_gst_breakdown(subtotal_paise),
        }

    net_payable_paise = max(0, subtotal_paise - discount_paise)

    return {
        "valid": True,
        "error": None,
        "coupon": {
            "id": coupon.id,
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
            "min_order_paise": coupon.min_order_paise,
            "max_discount_paise": coupon.max_discount_paise,
        },
        "discount_paise": discount_paise,
        "discount_inr": discount_paise / 100.0,
        "subtotal_paise": subtotal_paise,
        "subtotal_inr": subtotal_paise / 100.0,
        "net_payable_paise": net_payable_paise,
        "net_payable_inr": net_payable_paise / 100.0,
        "gst_breakdown": calculate_gst_breakdown(net_payable_paise),
    }


@transaction.atomic
def redeem_coupon(coupon_id_or_instance) -> Coupon:
    """
    Atomically increments times_used for a coupon.
    Prevents race conditions by using select_for_update() and F() expression.
    """
    if isinstance(coupon_id_or_instance, Coupon):
        coupon_id = coupon_id_or_instance.id
    elif isinstance(coupon_id_or_instance, int):
        coupon_id = coupon_id_or_instance
    else:
        coupon = Coupon.objects.select_for_update().get(code__iexact=str(coupon_id_or_instance).strip())
        coupon_id = coupon.id

    coupon = Coupon.objects.select_for_update().get(id=coupon_id)
    if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
        raise ValueError("Coupon has already reached its maximum usage limit.")

    Coupon.objects.filter(id=coupon.id).update(times_used=F('times_used') + 1)
    coupon.refresh_from_db()
    return coupon


@transaction.atomic
def create_order(user, raw_items: list, coupon_code: str = None):
    """
    Server-authoritative order creation:
    1. Validates non-empty cart items.
    2. Validates product existence and active status.
    3. Validates purchase eligibility (no prior ownership, no active pass unlock, no intra-cart overlap).
    4. Server recomputes item prices, upgrade credits, and subtotal from source database rows.
    5. Validates and applies optional promotional coupon against recomputed subtotal.
    6. Computes 18% inclusive GST split.
    7. Atomically creates Order (status PENDING) and itemized OrderItem snapshots.
    """
    from rest_framework.exceptions import ValidationError
    from apps.products.models import Product
    from apps.products.services import (
        validate_cart_items_eligibility,
        recalculate_cart_pricing,
    )
    from .models import Order, OrderItem
    from .gst import calculate_inclusive_gst

    if not raw_items:
        raise ValidationError({"items": ["Cart is empty. Please provide at least one product item."]})

    # Extract product IDs
    product_ids = []
    for item in raw_items:
        if isinstance(item, dict):
            pid = item.get('product_id') or item.get('id')
            if pid:
                product_ids.append(pid)
        elif isinstance(item, (int, str)):
            try:
                product_ids.append(int(item))
            except ValueError:
                pass

    if not product_ids:
        raise ValidationError({"items": ["No valid product IDs found in items list."]})

    products = list(Product.objects.filter(id__in=product_ids).select_related(
        'academic_class', 'subject', 'chapter'
    ).prefetch_related('prices'))

    found_ids = {p.id for p in products}
    missing_ids = [pid for pid in product_ids if pid not in found_ids]
    if missing_ids:
        raise ValidationError({"items": [f"Product ID {pid} does not exist." for pid in missing_ids]})

    inactive = [p.title for p in products if not p.is_active]
    if inactive:
        raise ValidationError({"items": [f"Product '{t}' is inactive and cannot be purchased." for t in inactive]})

    product_map = {p.id: p for p in products}
    ordered_products = [product_map[pid] for pid in product_ids]

    # Validate eligibility (ownership, pass unlocks, intra-cart conflicts)
    is_valid, errors = validate_cart_items_eligibility(user, ordered_products)
    if not is_valid:
        raise ValidationError({"items": errors})

    # Server-authoritative price recalculation (ignores any client prices)
    cart_data = recalculate_cart_pricing(user, ordered_products)
    gross_amount_paise = cart_data['pricing']['total_base_price_paise']
    upgrade_discount_paise = cart_data['pricing']['total_upgrade_credit_paise']
    subtotal_paise = cart_data['pricing']['subtotal_paise']

    # Coupon validation
    coupon_obj = None
    coupon_discount_paise = 0
    if coupon_code and coupon_code.strip():
        coupon_res = validate_and_apply_coupon(coupon_code, subtotal_paise, user=user)
        if not coupon_res['valid']:
            raise ValidationError({"coupon": coupon_res['error']})
        coupon_obj = Coupon.objects.get(id=coupon_res['coupon']['id'])
        coupon_discount_paise = coupon_res['discount_paise']

    # Final payable calculation
    net_payable_paise = max(0, subtotal_paise - coupon_discount_paise)

    # 18% inclusive GST split
    gst = calculate_inclusive_gst(net_payable_paise)
    taxable_base_paise = gst['base_taxable_paise']
    gst_amount_paise = gst['total_gst_paise']

    # Create Order record (status PENDING)
    order = Order.objects.create(
        user=user,
        order_number=Order.generate_order_number(),
        status=Order.STATUS_PENDING,
        gross_amount_paise=gross_amount_paise,
        upgrade_discount_paise=upgrade_discount_paise,
        coupon=coupon_obj,
        coupon_code=coupon_obj.code if coupon_obj else None,
        coupon_discount_paise=coupon_discount_paise,
        taxable_base_paise=taxable_base_paise,
        gst_amount_paise=gst_amount_paise,
        net_payable_paise=net_payable_paise,
    )

    # Create OrderItem records
    for item in cart_data['items']:
        OrderItem.objects.create(
            order=order,
            product=product_map[item['product_id']],
            unit_price_paise=item['base_price_paise'],
            upgrade_credit_paise=item['upgrade_credit_paise'],
            net_price_paise=item['final_price_paise'],
        )

    return order


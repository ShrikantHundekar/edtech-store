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

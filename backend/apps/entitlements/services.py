from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from .models import Entitlement


def has_access_to_chapter(user, chapter) -> bool:
    """
    Evaluates whether a given user has active entitlement access to a chapter.
    Free samples are accessible to everyone.
    Admins have full access.
    Students require an active entitlement (Chapter, Subject Pack, or Class Pass).
    """
    if not chapter:
        return False

    # 1. Free sample check
    if chapter.is_free_sample:
        return True

    # 2. Authentication check
    if not user or not user.is_authenticated:
        return False

    # 3. Admin bypass
    if getattr(user, 'role', None) == 'ADMIN' or getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True

    # 4. Entitlement query
    now = timezone.now()
    active_entitlements = Entitlement.objects.filter(
        user=user,
        status='ACTIVE',
    ).filter(
        Q(access_type='LIFETIME') | Q(access_type='TIME_BOUND', valid_until__gt=now)
    )

    subject = chapter.subject
    class_id = subject.academic_class_id

    # Check Chapter license OR Subject Pack license OR Class Pass license
    has_access = active_entitlements.filter(
        Q(product_type='CHAPTER', scope_id=chapter.id) |
        Q(product_type='SUBJECT', scope_id=subject.id) |
        Q(product_type='CLASS_PASS', scope_id=class_id)
    ).exists()

    return has_access


def has_access_to_material(user, material) -> bool:
    """
    Evaluates whether a given user has active entitlement access to a study material.
    Delegates to has_access_to_chapter based on the parent chapter.
    """
    if not material:
        return False
    return has_access_to_chapter(user, material.chapter)


def calculate_pass_validity_window(user, class_id: int, duration_days: int) -> dict:
    """
    Calculates time-bound validity window for a class pass (e.g. 30 days or 365 days).
    Standard activation:
      If no active pass: valid_until = now() + duration_days
    Early renewal (Pass Stacking):
      If an active pass exists: new_valid_until = existing_valid_until + duration_days
    """
    now = timezone.now()
    active_pass = None

    if user and user.is_authenticated:
        active_pass = Entitlement.objects.filter(
            user=user,
            product_type='CLASS_PASS',
            scope_id=class_id,
            status='ACTIVE',
            valid_until__gt=now
        ).order_by('-valid_until').first()

    if active_pass:
        base_time = active_pass.valid_until
        is_renewal = True
        valid_from = now
        valid_until = base_time + timedelta(days=duration_days)
        remaining_seconds = (active_pass.valid_until - now).total_seconds()
        remaining_days = max(0, round(remaining_seconds / 86400))
        existing_expiry = active_pass.valid_until
    else:
        base_time = now
        is_renewal = False
        valid_from = now
        valid_until = valid_from + timedelta(days=duration_days)
        remaining_days = 0
        existing_expiry = None

    return {
        "class_id": class_id,
        "duration_days": duration_days,
        "is_renewal": is_renewal,
        "base_time": base_time,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "existing_valid_until": existing_expiry,
        "remaining_active_days": remaining_days,
    }


def provision_class_pass_entitlement(user, class_id: int, duration_days: int, order=None) -> Entitlement:
    """
    Provisions or extends an active time-bound Class Pass entitlement for a student.
    Sets valid_until based on early renewal stacking if a previous active pass exists.
    """
    window = calculate_pass_validity_window(user, class_id, duration_days)

    entitlement = Entitlement.objects.create(
        user=user,
        product_type='CLASS_PASS',
        scope_id=class_id,
        access_type='TIME_BOUND',
        valid_from=window["valid_from"],
        valid_until=window["valid_until"],
        status='ACTIVE',
        order=order
    )
    return entitlement


def provision_order_entitlements(order) -> list:
    """
    Provisions access entitlements for all items in an Order.
    Handles:
    - Chapter Notes -> CHAPTER entitlement (LIFETIME)
    - Subject Pack -> SUBJECT entitlement (LIFETIME)
    - Monthly/Annual Pass -> CLASS_PASS entitlement (TIME_BOUND, with pass renewal stacking)
    - Custom Bundle -> BUNDLE entitlement and associated included subjects/chapters
    - Atomically redeems order coupon if present.
    """
    from apps.products.models import Product
    from apps.orders.services import redeem_coupon

    user = order.user
    created_entitlements = []

    for item in order.items.select_related('product', 'product__chapter', 'product__subject').all():
        prod = item.product

        if prod.product_type == Product.PRODUCT_TYPE_CHAPTER_NOTES:
            ch_id = prod.chapter_id
            if ch_id:
                ent, _ = Entitlement.objects.get_or_create(
                    user=user,
                    product_type='CHAPTER',
                    scope_id=ch_id,
                    defaults={
                        'access_type': 'LIFETIME',
                        'status': 'ACTIVE',
                        'order': order
                    }
                )
                created_entitlements.append(ent)

        elif prod.product_type == Product.PRODUCT_TYPE_SUBJECT_PACK:
            sub_id = prod.subject_id
            if sub_id:
                ent, _ = Entitlement.objects.get_or_create(
                    user=user,
                    product_type='SUBJECT',
                    scope_id=sub_id,
                    defaults={
                        'access_type': 'LIFETIME',
                        'status': 'ACTIVE',
                        'order': order
                    }
                )
                created_entitlements.append(ent)

        elif prod.product_type in (Product.PRODUCT_TYPE_MONTHLY_PASS, Product.PRODUCT_TYPE_ANNUAL_PASS):
            class_id = prod.academic_class_id
            duration = prod.pass_duration_days or (365 if prod.product_type == Product.PRODUCT_TYPE_ANNUAL_PASS else 30)
            if class_id:
                ent = provision_class_pass_entitlement(user, class_id, duration, order=order)
                created_entitlements.append(ent)

        elif prod.product_type == Product.PRODUCT_TYPE_BUNDLE:
            ent, _ = Entitlement.objects.get_or_create(
                user=user,
                product_type='BUNDLE',
                scope_id=prod.id,
                defaults={
                    'access_type': 'LIFETIME',
                    'status': 'ACTIVE',
                    'order': order
                }
            )
            created_entitlements.append(ent)
            for bundle_item in prod.bundle_items.all():
                if bundle_item.target_type == 'SUBJECT' and bundle_item.target_id:
                    sub_ent, _ = Entitlement.objects.get_or_create(
                        user=user,
                        product_type='SUBJECT',
                        scope_id=bundle_item.target_id,
                        defaults={'access_type': 'LIFETIME', 'status': 'ACTIVE', 'order': order}
                    )
                    created_entitlements.append(sub_ent)
                elif bundle_item.target_type == 'CHAPTER' and bundle_item.target_id:
                    ch_ent, _ = Entitlement.objects.get_or_create(
                        user=user,
                        product_type='CHAPTER',
                        scope_id=bundle_item.target_id,
                        defaults={'access_type': 'LIFETIME', 'status': 'ACTIVE', 'order': order}
                    )
                    created_entitlements.append(ch_ent)

    if order.coupon:
        redeem_coupon(order.coupon)

    return created_entitlements


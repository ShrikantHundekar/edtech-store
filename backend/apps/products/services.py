from apps.orders.gst import calculate_inclusive_gst, calculate_gst_breakdown



def check_product_purchase_eligibility(user, product) -> tuple:
    """
    Evaluates a user's eligibility to purchase a specific product based on existing entitlements.
    Returns:
        tuple (can_purchase: bool, state: str, reason: str)
        where state is strictly one of: 'BUY', 'OWNED', 'UPGRADE', 'UNLOCKED_VIA_PASS'
    """
    from apps.entitlements.models import Entitlement
    from apps.products.models import Product
    from django.utils import timezone
    from django.db.models import Q

    if not product.is_active:
        return False, 'UNAVAILABLE', 'This product is currently inactive.'

    # Free sample is unlocked without requiring purchase
    if product.product_type == Product.PRODUCT_TYPE_FREE_SAMPLE:
        return False, 'OWNED', 'Free sample is unlocked without requiring purchase.'

    # Unauthenticated users default to BUY
    if not user or not user.is_authenticated:
        return True, 'BUY', 'Available for purchase.'

    now = timezone.now()
    active_entitlements = Entitlement.objects.filter(
        user=user,
        status='ACTIVE'
    ).filter(
        Q(access_type='LIFETIME') | Q(access_type='TIME_BOUND', valid_until__gt=now)
    )

    # 1. Determine target academic class and check active Class Pass
    target_class_id = None
    if product.academic_class_id:
        target_class_id = product.academic_class_id
    elif product.subject and product.subject.academic_class_id:
        target_class_id = product.subject.academic_class_id
    elif product.chapter and product.chapter.subject and product.chapter.subject.academic_class_id:
        target_class_id = product.chapter.subject.academic_class_id

    # If the product is Chapter Notes or Subject Pack, check if unlocked via Class Pass
    if target_class_id and product.product_type in (
        Product.PRODUCT_TYPE_CHAPTER_NOTES,
        Product.PRODUCT_TYPE_SUBJECT_PACK
    ):
        has_active_pass = active_entitlements.filter(
            product_type='CLASS_PASS',
            scope_id=target_class_id
        ).exists()
        if has_active_pass:
            return False, 'UNLOCKED_VIA_PASS', 'Unlocked with Class Pass'

    # 2. Check CHAPTER_NOTES eligibility
    if product.product_type == Product.PRODUCT_TYPE_CHAPTER_NOTES:
        chapter = product.chapter
        if not chapter:
            return False, 'UNAVAILABLE', 'Chapter reference is missing.'

        subject_id = chapter.subject_id
        # Check if student owns the Subject Pack
        if subject_id and active_entitlements.filter(product_type='SUBJECT', scope_id=subject_id).exists():
            return False, 'OWNED', 'Owned (via Subject Pack)'

        # Check if student already owns this chapter
        if active_entitlements.filter(product_type='CHAPTER', scope_id=chapter.id).exists():
            return False, 'OWNED', 'Owned'

        return True, 'BUY', 'Available for purchase.'

    # 3. Check SUBJECT_PACK eligibility
    if product.product_type == Product.PRODUCT_TYPE_SUBJECT_PACK:
        subject = product.subject
        if not subject:
            return False, 'UNAVAILABLE', 'Subject reference is missing.'

        # Check if student already owns this Subject Pack
        if active_entitlements.filter(product_type='SUBJECT', scope_id=subject.id).exists():
            return False, 'OWNED', 'Owned'

        # Check if student owns any individual chapters in this subject (Upgrade state)
        owned_chapter_ids = list(active_entitlements.filter(
            product_type='CHAPTER'
        ).values_list('scope_id', flat=True))

        if subject.chapters.filter(id__in=owned_chapter_ids).exists():
            return True, 'UPGRADE', 'Eligible for Subject Pack upgrade credit.'

        return True, 'BUY', 'Available for purchase.'

    # 4. Check MONTHLY_PASS & ANNUAL_PASS
    if product.product_type in (Product.PRODUCT_TYPE_MONTHLY_PASS, Product.PRODUCT_TYPE_ANNUAL_PASS):
        return True, 'BUY', 'Available for purchase.'

    # 5. Check BUNDLE
    if product.product_type == Product.PRODUCT_TYPE_BUNDLE:
        if active_entitlements.filter(product_type='BUNDLE', scope_id=product.id).exists():
            return False, 'OWNED', 'Owned'
        return True, 'BUY', 'Available for purchase.'

    return True, 'BUY', 'Available for purchase.'


def validate_cart_items_eligibility(user, products: list) -> tuple:
    """
    Validates a list of Product instances for overlapping or ineligible purchase.
    Rejects:
    - Products already owned or unlocked via Class Pass by the user.
    - Duplicate products in the same cart.
    - Intra-cart conflicts: e.g. purchasing both a Subject Pack and Chapter within that subject.
    - Intra-cart conflicts: e.g. purchasing a Class Pass and any Subject/Chapter within that class.
    
    Returns:
        tuple (is_valid: bool, errors: list[str])
    """
    from apps.products.models import Product

    errors = []
    seen_product_ids = set()
    cart_class_pass_ids = set()
    cart_subject_pack_ids = set()
    cart_chapter_items = []

    for p in products:
        # Check duplicate
        if p.id in seen_product_ids:
            errors.append(f"Duplicate item in cart: '{p.title}'.")
        seen_product_ids.add(p.id)

        # Check user ownership / active pass
        can_buy, state, reason = check_product_purchase_eligibility(user, p)
        if not can_buy:
            errors.append(f"Cannot purchase '{p.title}': {reason} (Status: {state}).")

        # Categorize for intra-cart conflict checks
        if p.product_type in (Product.PRODUCT_TYPE_MONTHLY_PASS, Product.PRODUCT_TYPE_ANNUAL_PASS):
            if p.academic_class_id:
                cart_class_pass_ids.add(p.academic_class_id)
        elif p.product_type == Product.PRODUCT_TYPE_SUBJECT_PACK:
            if p.subject_id:
                cart_subject_pack_ids.add(p.subject_id)
        elif p.product_type == Product.PRODUCT_TYPE_CHAPTER_NOTES:
            if p.chapter:
                cart_chapter_items.append(p)

    # Intra-cart conflict: Class Pass + Subject / Chapter in same class
    for p in products:
        if p.product_type in (Product.PRODUCT_TYPE_CHAPTER_NOTES, Product.PRODUCT_TYPE_SUBJECT_PACK):
            target_class_id = None
            if p.academic_class_id:
                target_class_id = p.academic_class_id
            elif p.subject and p.subject.academic_class_id:
                target_class_id = p.subject.academic_class_id
            elif p.chapter and p.chapter.subject and p.chapter.subject.academic_class_id:
                target_class_id = p.chapter.subject.academic_class_id

            if target_class_id and target_class_id in cart_class_pass_ids:
                errors.append(
                    f"Cart conflict: '{p.title}' is already unlocked by the Class Pass in your cart."
                )

    # Intra-cart conflict: Subject Pack + Chapter in same subject
    for p in cart_chapter_items:
        if p.chapter and p.chapter.subject_id in cart_subject_pack_ids:
            errors.append(
                f"Cart conflict: Cannot purchase chapter note '{p.title}' together with its Subject Pack in the same cart."
            )

    return (len(errors) == 0, errors)


def calculate_subject_pack_upgrade_credit(user, product) -> dict:
    """
    Calculates upgrade discount credit for students upgrading to a Subject Pack:
    Formula:
      Upgrade Price = max(0, Subject Pack Price - Sum of Amounts Paid for Owned Chapters)
      Floors at 0 paise if total prior purchases exceed pack price.
    """
    from apps.entitlements.models import Entitlement
    from apps.products.models import Product
    from django.utils import timezone
    from django.db.models import Q

    base_price = product.current_price_paise

    if product.product_type != Product.PRODUCT_TYPE_SUBJECT_PACK:
        pass_renewal = None
        if product.product_type in (Product.PRODUCT_TYPE_MONTHLY_PASS, Product.PRODUCT_TYPE_ANNUAL_PASS):
            from apps.entitlements.services import calculate_pass_validity_window
            duration_days = product.pass_duration_days or 30
            if product.academic_class_id:
                pass_renewal = calculate_pass_validity_window(user, product.academic_class_id, duration_days)

        return {
            "product_id": product.id,
            "title": product.title,
            "product_type": product.product_type,
            "base_price_paise": base_price,
            "base_price_inr": base_price / 100.0,
            "upgrade_credit_paise": 0,
            "upgrade_credit_inr": 0.0,
            "payable_price_paise": base_price,
            "payable_price_inr": base_price / 100.0,
            "owned_chapters_count": 0,
            "owned_chapters": [],
            "renewal_preview": pass_renewal,
            "gst_breakdown": calculate_gst_breakdown(base_price),
        }

    if not user or not user.is_authenticated or not product.subject:
        return {
            "product_id": product.id,
            "title": product.title,
            "product_type": product.product_type,
            "base_price_paise": base_price,
            "base_price_inr": base_price / 100.0,
            "upgrade_credit_paise": 0,
            "upgrade_credit_inr": 0.0,
            "payable_price_paise": base_price,
            "payable_price_inr": base_price / 100.0,
            "owned_chapters_count": 0,
            "owned_chapters": [],
            "gst_breakdown": calculate_gst_breakdown(base_price),
        }

    now = timezone.now()
    subject_chapters = {ch.id: ch for ch in product.subject.chapters.all()}

    entitlements = Entitlement.objects.filter(
        user=user,
        status='ACTIVE',
        product_type='CHAPTER',
        scope_id__in=subject_chapters.keys()
    ).filter(
        Q(access_type='LIFETIME') | Q(access_type='TIME_BOUND', valid_until__gt=now)
    ).select_related('order').order_by('scope_id', '-created_at')

    owned_chapters_dict = {}
    for ent in entitlements:
        ch_id = ent.scope_id
        if ch_id in owned_chapters_dict:
            continue

        ch = subject_chapters.get(ch_id)
        if not ch:
            continue

        credit_amount = 0
        if ent.order:
            order_item = ent.order.items.filter(
                product__product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
                product__chapter_id=ch_id
            ).first()
            if order_item:
                credit_amount = order_item.net_price_paise

        if credit_amount == 0:
            ch_prod = Product.objects.filter(
                product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
                chapter_id=ch_id
            ).first()
            if ch_prod:
                credit_amount = ch_prod.current_price_paise

        owned_chapters_dict[ch_id] = {
            "chapter_id": ch.id,
            "chapter_title": ch.title,
            "chapter_number": ch.chapter_number,
            "credit_paise": credit_amount,
            "credit_inr": credit_amount / 100.0,
        }

    owned_chapters_list = list(owned_chapters_dict.values())
    total_credit = sum(item["credit_paise"] for item in owned_chapters_list)

    # Formula: Upgrade Price = max(0, Subject Pack Price - Sum of Amounts Paid for Owned Chapters)
    payable_price = max(0, base_price - total_credit)
    upgrade_credit_applied = min(total_credit, base_price)

    return {
        "product_id": product.id,
        "title": product.title,
        "product_type": product.product_type,
        "base_price_paise": base_price,
        "base_price_inr": base_price / 100.0,
        "upgrade_credit_paise": upgrade_credit_applied,
        "upgrade_credit_inr": upgrade_credit_applied / 100.0,
        "total_credit_available_paise": total_credit,
        "payable_price_paise": payable_price,
        "payable_price_inr": payable_price / 100.0,
        "owned_chapters_count": len(owned_chapters_list),
        "owned_chapters": owned_chapters_list,
        "gst_breakdown": calculate_gst_breakdown(payable_price),
    }


def recalculate_cart_pricing(user, products: list) -> dict:
    """
    Recalculates cart line items and pricing strictly from source database records.
    Completely ignores any client-supplied prices or tampering.

    Computes:
    - Source unit price from Price table for each product.
    - Upgrade credit for Subject Packs based on user's prior purchases.
    - Early renewal stacking info for Class Passes.
    - Net final line item price.
    - Cart subtotal (sum of all line item final prices).
    - 18% inclusive GST breakdown on the cart subtotal.
    """
    from apps.products.models import Product
    from apps.entitlements.services import calculate_pass_validity_window

    line_items = []

    for product in products:
        base_price = product.current_price_paise
        upgrade_credit = 0
        final_price = base_price
        renewal_preview = None
        details = {}

        if product.product_type == Product.PRODUCT_TYPE_SUBJECT_PACK:
            calc = calculate_subject_pack_upgrade_credit(user, product)
            upgrade_credit = calc["upgrade_credit_paise"]
            final_price = calc["payable_price_paise"]
            details = {
                "owned_chapters_count": calc.get("owned_chapters_count", 0),
                "total_credit_available_paise": calc.get("total_credit_available_paise", 0),
            }
        elif product.product_type in (Product.PRODUCT_TYPE_MONTHLY_PASS, Product.PRODUCT_TYPE_ANNUAL_PASS):
            duration_days = product.pass_duration_days or 30
            if product.academic_class_id:
                renewal_preview = calculate_pass_validity_window(user, product.academic_class_id, duration_days)

        line_item = {
            "product_id": product.id,
            "title": product.title,
            "product_type": product.product_type,
            "academic_class_id": product.academic_class_id,
            "subject_id": product.subject_id,
            "chapter_id": product.chapter_id,
            "base_price_paise": base_price,
            "base_price_inr": base_price / 100.0,
            "upgrade_credit_paise": upgrade_credit,
            "upgrade_credit_inr": upgrade_credit / 100.0,
            "final_price_paise": final_price,
            "final_price_inr": final_price / 100.0,
            "currency": "INR",
            "renewal_preview": renewal_preview,
            **details,
        }
        line_items.append(line_item)

    total_base_price_paise = sum(item["base_price_paise"] for item in line_items)
    total_upgrade_credit_paise = sum(item["upgrade_credit_paise"] for item in line_items)
    subtotal_paise = sum(item["final_price_paise"] for item in line_items)
    gst_breakdown = calculate_gst_breakdown(subtotal_paise)

    return {
        "items": line_items,
        "items_count": len(line_items),
        "pricing": {
            "total_base_price_paise": total_base_price_paise,
            "total_base_price_inr": total_base_price_paise / 100.0,
            "total_upgrade_credit_paise": total_upgrade_credit_paise,
            "total_upgrade_credit_inr": total_upgrade_credit_paise / 100.0,
            "subtotal_paise": subtotal_paise,
            "subtotal_inr": subtotal_paise / 100.0,
            "currency": "INR",
            "gst_breakdown": gst_breakdown,
        }
    }




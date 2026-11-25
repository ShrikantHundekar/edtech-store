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
                target_sub_id = bundle_item.subject_id or getattr(bundle_item, 'target_id', None)
                target_ch_id = bundle_item.chapter_id or getattr(bundle_item, 'target_id', None)
                if bundle_item.target_type == 'SUBJECT' and target_sub_id:
                    sub_ent, _ = Entitlement.objects.get_or_create(
                        user=user,
                        product_type='SUBJECT',
                        scope_id=target_sub_id,
                        defaults={'access_type': 'LIFETIME', 'status': 'ACTIVE', 'order': order}
                    )
                    created_entitlements.append(sub_ent)
                elif bundle_item.target_type == 'CHAPTER' and target_ch_id:
                    ch_ent, _ = Entitlement.objects.get_or_create(
                        user=user,
                        product_type='CHAPTER',
                        scope_id=target_ch_id,
                        defaults={'access_type': 'LIFETIME', 'status': 'ACTIVE', 'order': order}
                    )
                    created_entitlements.append(ch_ent)

    if order.coupon:
        redeem_coupon(order.coupon)

    return created_entitlements


def manual_grant_entitlement(
    admin_user,
    student_user,
    product_type: str,
    scope_id: int,
    reason: str,
    access_type: str = 'LIFETIME',
    valid_until=None
) -> tuple:
    """
    Manually grants an entitlement to a student by an administrator with audit logging.
    Requirement:
    - Reason field is strictly mandatory.
    - Creates ManualAccessLog recording admin_id, student_id, action, reason, timestamp.
    """
    from .models import ManualAccessLog

    if not reason or not str(reason).strip():
        raise ValueError("Reason field is strictly mandatory.")

    if not admin_user or (not getattr(admin_user, 'is_admin', False) and not getattr(admin_user, 'is_staff', False)):
        raise PermissionError("Administrator privileges required for manual entitlement grant.")

    if not student_user:
        raise ValueError("Valid student user is required.")

    valid_types = [choice[0] for choice in Entitlement.PRODUCT_TYPE_CHOICES]
    if product_type not in valid_types:
        raise ValueError(f"Invalid product_type '{product_type}'. Must be one of {valid_types}.")

    entitlement, _ = Entitlement.objects.update_or_create(
        user=student_user,
        product_type=product_type,
        scope_id=scope_id,
        defaults={
            'access_type': access_type,
            'valid_until': valid_until,
            'status': 'ACTIVE',
            'order': None,
        }
    )

    log = ManualAccessLog.objects.create(
        admin=admin_user,
        student=student_user,
        action='GRANT',
        entitlement=entitlement,
        reason=reason.strip()
    )

    return entitlement, log


def manual_revoke_entitlement(admin_user, entitlement_id: int, reason: str) -> tuple:
    """
    Manually revokes an entitlement by an administrator with audit logging.
    Requirement:
    - Reason field is strictly mandatory.
    - Updates entitlement status to REVOKED and logs audit entry.
    """
    from .models import ManualAccessLog

    if not reason or not str(reason).strip():
        raise ValueError("Reason field is strictly mandatory.")

    if not admin_user or (not getattr(admin_user, 'is_admin', False) and not getattr(admin_user, 'is_staff', False)):
        raise PermissionError("Administrator privileges required for manual entitlement revoke.")

    entitlement = Entitlement.objects.get(id=entitlement_id)
    entitlement.status = 'REVOKED'
    entitlement.save(update_fields=['status', 'updated_at'])

    log = ManualAccessLog.objects.create(
        admin=admin_user,
        student=entitlement.user,
        action='REVOKE',
        entitlement=entitlement,
        reason=reason.strip()
    )

    return entitlement, log


def get_student_library_data(user) -> dict:
    """
    Returns complete personalized student library hub data:
    1. Active & historical class passes with live countdown metrics.
    2. Owned chapters (direct purchase, subject pack unlock, or active class pass unlock).
    3. Owned subject packs and bundles.
    4. Attached downloadable/streamable study materials with protected stream URLs.
    """
    from django.db.models import Q
    from apps.catalog.models import Chapter, Subject, ClassLevel
    from apps.entitlements.models import Entitlement

    now = timezone.now()
    active_entitlements = Entitlement.objects.filter(
        user=user,
        status='ACTIVE'
    ).filter(
        Q(access_type='LIFETIME') | Q(access_type='TIME_BOUND', valid_until__gt=now)
    )

    # 1. Passes
    passes_qs = Entitlement.objects.filter(
        user=user,
        product_type='CLASS_PASS'
    ).order_by('-valid_until')

    passes = []
    active_class_ids = set()
    for p in passes_qs:
        is_active = p.is_currently_active
        rem_seconds = 0
        rem_days = 0
        if p.valid_until and p.valid_until > now and p.status == 'ACTIVE':
            rem_seconds = (p.valid_until - now).total_seconds()
            rem_days = max(0, int(rem_seconds // 86400) + (1 if rem_seconds % 86400 > 0 else 0))

        if is_active:
            active_class_ids.add(p.scope_id)

        class_obj = ClassLevel.objects.filter(id=p.scope_id).select_related('board').first()
        passes.append({
            'id': p.id,
            'class_id': p.scope_id,
            'class_name': class_obj.name if class_obj else f"Class {p.scope_id}",
            'board_name': class_obj.board.name if class_obj and class_obj.board else 'CBSE',
            'valid_from': p.valid_from.isoformat() if p.valid_from else None,
            'valid_until': p.valid_until.isoformat() if p.valid_until else None,
            'is_active': is_active,
            'status': p.status,
            'remaining_days': rem_days,
            'remaining_seconds': int(rem_seconds),
            'countdown_text': f"{rem_days} days left" if is_active and rem_days > 0 else ("Expires today" if is_active else "Expired"),
        })

    # 2. Owned chapter IDs and subject IDs
    direct_chapter_ids = set(active_entitlements.filter(product_type='CHAPTER').values_list('scope_id', flat=True))
    direct_subject_ids = set(active_entitlements.filter(product_type='SUBJECT').values_list('scope_id', flat=True))

    all_chapters = Chapter.objects.select_related(
        'subject__academic_class__board'
    ).prefetch_related('materials').all().order_by(
        'subject__academic_class__id', 'subject__id', 'chapter_number'
    )

    owned_chapters = []
    for ch in all_chapters:
        unlocked_via = None
        if ch.id in direct_chapter_ids:
            unlocked_via = 'CHAPTER'
        elif ch.subject_id in direct_subject_ids:
            unlocked_via = 'SUBJECT'
        elif ch.subject.academic_class_id in active_class_ids:
            unlocked_via = 'CLASS_PASS'
        elif ch.is_free_sample:
            unlocked_via = 'FREE_SAMPLE'

        if unlocked_via:
            materials_list = []
            for m in ch.materials.all():
                materials_list.append({
                    'id': m.id,
                    'title': m.title,
                    'mime_type': m.mime_type,
                    'file_size_bytes': m.file_size_bytes,
                    'stream_url': f"/api/v1/materials/{m.id}/stream/",
                })

            owned_chapters.append({
                'id': ch.id,
                'chapter_number': ch.chapter_number,
                'title': ch.title,
                'subject_id': ch.subject.id,
                'subject_name': ch.subject.name,
                'class_id': ch.subject.academic_class.id,
                'class_name': ch.subject.academic_class.name,
                'board_name': ch.subject.academic_class.board.name if ch.subject.academic_class.board else 'CBSE',
                'is_free_sample': ch.is_free_sample,
                'unlocked_via': unlocked_via,
                'materials': materials_list,
            })

    # 3. Owned Subjects
    owned_subjects = []
    if direct_subject_ids:
        for s in Subject.objects.filter(id__in=direct_subject_ids).select_related('academic_class__board'):
            owned_subjects.append({
                'id': s.id,
                'name': s.name,
                'class_name': s.academic_class.name,
                'board_name': s.academic_class.board.name if s.academic_class.board else 'CBSE',
                'chapters_count': s.chapters.count(),
            })

    return {
        'passes': passes,
        'chapters': owned_chapters,
        'subjects': owned_subjects,
        'stats': {
            'active_passes_count': len([p for p in passes if p['is_active']]),
            'total_chapters_unlocked': len(owned_chapters),
            'direct_chapters_count': len(direct_chapter_ids),
            'direct_subjects_count': len(direct_subject_ids),
        }
    }



def get_student_library_data(user) -> dict:
    """
    Returns complete personalized student library hub data:
    1. Active & historical class passes with live countdown metrics.
    2. Owned chapters (direct purchase, subject pack unlock, or active class pass unlock).
    3. Owned subject packs and bundles.
    4. Attached downloadable/streamable study materials with protected stream URLs.
    """
    from django.db.models import Q
    from apps.catalog.models import Chapter, Subject, ClassLevel
    from apps.entitlements.models import Entitlement

    now = timezone.now()
    active_entitlements = Entitlement.objects.filter(
        user=user,
        status='ACTIVE'
    ).filter(
        Q(access_type='LIFETIME') | Q(access_type='TIME_BOUND', valid_until__gt=now)
    )

    # 1. Passes
    passes_qs = Entitlement.objects.filter(
        user=user,
        product_type='CLASS_PASS'
    ).order_by('-valid_until')

    passes = []
    active_class_ids = set()
    for p in passes_qs:
        is_active = p.is_currently_active
        rem_seconds = 0
        rem_days = 0
        if p.valid_until and p.valid_until > now and p.status == 'ACTIVE':
            rem_seconds = (p.valid_until - now).total_seconds()
            rem_days = max(0, int(rem_seconds // 86400) + (1 if rem_seconds % 86400 > 0 else 0))

        if is_active:
            active_class_ids.add(p.scope_id)

        class_obj = ClassLevel.objects.filter(id=p.scope_id).select_related('board').first()
        passes.append({
            'id': p.id,
            'class_id': p.scope_id,
            'class_name': class_obj.name if class_obj else f"Class {p.scope_id}",
            'board_name': class_obj.board.name if class_obj and class_obj.board else 'CBSE',
            'valid_from': p.valid_from.isoformat() if p.valid_from else None,
            'valid_until': p.valid_until.isoformat() if p.valid_until else None,
            'is_active': is_active,
            'status': p.status,
            'remaining_days': rem_days,
            'remaining_seconds': int(rem_seconds),
            'countdown_text': f"{rem_days} days left" if is_active and rem_days > 0 else ("Expires today" if is_active else "Expired"),
        })

    # 2. Owned chapter IDs and subject IDs
    direct_chapter_ids = set(active_entitlements.filter(product_type='CHAPTER').values_list('scope_id', flat=True))
    direct_subject_ids = set(active_entitlements.filter(product_type='SUBJECT').values_list('scope_id', flat=True))

    all_chapters = Chapter.objects.select_related(
        'subject__academic_class__board'
    ).prefetch_related('materials').all().order_by(
        'subject__academic_class__id', 'subject__id', 'chapter_number'
    )

    owned_chapters = []
    for ch in all_chapters:
        unlocked_via = None
        if ch.id in direct_chapter_ids:
            unlocked_via = 'CHAPTER'
        elif ch.subject_id in direct_subject_ids:
            unlocked_via = 'SUBJECT'
        elif ch.subject.academic_class_id in active_class_ids:
            unlocked_via = 'CLASS_PASS'
        elif ch.is_free_sample:
            unlocked_via = 'FREE_SAMPLE'

        if unlocked_via:
            materials_list = []
            for m in ch.materials.all():
                materials_list.append({
                    'id': m.id,
                    'title': m.title,
                    'mime_type': m.mime_type,
                    'file_size_bytes': m.file_size_bytes,
                    'stream_url': f"/api/v1/materials/{m.id}/stream/",
                })

            owned_chapters.append({
                'id': ch.id,
                'chapter_number': ch.chapter_number,
                'title': ch.title,
                'subject_id': ch.subject.id,
                'subject_name': ch.subject.name,
                'class_id': ch.subject.academic_class.id,
                'class_name': ch.subject.academic_class.name,
                'board_name': ch.subject.academic_class.board.name if ch.subject.academic_class.board else 'CBSE',
                'is_free_sample': ch.is_free_sample,
                'unlocked_via': unlocked_via,
                'materials': materials_list,
            })

    # 3. Owned Subjects
    owned_subjects = []
    if direct_subject_ids:
        for s in Subject.objects.filter(id__in=direct_subject_ids).select_related('academic_class__board'):
            owned_subjects.append({
                'id': s.id,
                'name': s.name,
                'class_name': s.academic_class.name,
                'board_name': s.academic_class.board.name if s.academic_class.board else 'CBSE',
                'chapters_count': s.chapters.count(),
            })

    return {
        'passes': passes,
        'chapters': owned_chapters,
        'subjects': owned_subjects,
        'stats': {
            'active_passes_count': len([p for p in passes if p['is_active']]),
            'total_chapters_unlocked': len(owned_chapters),
            'direct_chapters_count': len(direct_chapter_ids),
            'direct_subjects_count': len(direct_subject_ids),
        }
    }




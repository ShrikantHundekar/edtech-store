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

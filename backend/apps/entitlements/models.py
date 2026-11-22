from django.db import models
from django.conf import settings
from django.utils import timezone


class EntitlementQuerySet(models.QuerySet):
    """
    Custom QuerySet for fast, indexed authorization queries.
    """
    def active(self):
        now = timezone.now()
        return self.filter(status='ACTIVE').filter(
            models.Q(access_type='LIFETIME') | models.Q(access_type='TIME_BOUND', valid_until__gt=now)
        )

    def for_user(self, user):
        return self.filter(user=user)

    def is_entitled(self, user, product_type: str, scope_id: int) -> bool:
        return self.for_user(user).active().filter(
            product_type=product_type,
            scope_id=scope_id
        ).exists()


class Entitlement(models.Model):
    """
    Represents an access license/entitlement granted to a student
    for educational content (Chapter, Subject Pack, or Class Pass).
    Decoupled from Orders to allow manual grants and fast, indexed access checks.
    """
    PRODUCT_TYPE_CHOICES = [
        ('CHAPTER', 'Chapter Notes'),
        ('SUBJECT', 'Subject Pack'),
        ('CLASS_PASS', 'Class Pass'),
        ('BUNDLE', 'Custom Bundle'),
    ]

    ACCESS_TYPE_CHOICES = [
        ('LIFETIME', 'Lifetime Access'),
        ('TIME_BOUND', 'Time Bound Access'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('REVOKED', 'Revoked'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='entitlements',
        db_column='user_id',
        help_text="Student who holds this entitlement"
    )
    product_type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPE_CHOICES,
        help_text="Scope tier: CHAPTER, SUBJECT, CLASS_PASS, or BUNDLE"
    )
    scope_id = models.BigIntegerField(
        help_text="Target entity ID: Chapter ID, Subject ID, or ClassLevel ID"
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entitlements',
        db_column='order_id',
        help_text="Originating order, or NULL if granted manually by administrator"
    )
    access_type = models.CharField(
        max_length=20,
        choices=ACCESS_TYPE_CHOICES,
        default='LIFETIME'
    )
    valid_from = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when access begins"
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when access expires (NULL for lifetime access)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text="Current state of access license"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EntitlementQuerySet.as_manager()

    class Meta:
        db_table = 'entitlements'
        ordering = ['-created_at']
        verbose_name = 'Entitlement'
        verbose_name_plural = 'Entitlements'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['product_type', 'scope_id']),
            models.Index(fields=['valid_until']),
            models.Index(fields=['user', 'status', 'product_type', 'scope_id'], name='entitlements_auth_check_idx'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.product_type} ({self.scope_id}) [{self.status}]"

    @property
    def is_currently_active(self):
        """
        Returns True if this entitlement is ACTIVE and not expired.
        """
        if self.status != 'ACTIVE':
            return False
        if self.access_type == 'TIME_BOUND' and self.valid_until:
            return self.valid_until > timezone.now()
        return True


class ManualAccessLog(models.Model):
    """
    Audit log recording administrative manual grants and revocations of content access.
    """
    ACTION_CHOICES = [
        ('GRANT', 'Grant Access'),
        ('REVOKE', 'Revoke Access'),
    ]

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_access_logs',
        db_column='admin_id',
        help_text="Administrator who performed the action"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_access_logs',
        db_column='student_id',
        help_text="Student whose access was modified"
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text="Action performed: GRANT or REVOKE"
    )
    entitlement = models.ForeignKey(
        Entitlement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='access_logs',
        db_column='entitlement_id',
        help_text="Associated entitlement record"
    )
    reason = models.TextField(
        help_text="Mandatory business reason for manual access change"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'manual_access_logs'
        ordering = ['-created_at']
        verbose_name = 'Manual Access Log'
        verbose_name_plural = 'Manual Access Logs'

    def __str__(self):
        return f"{self.action} for {self.student.email} by {self.admin.email} on {self.created_at.strftime('%Y-%m-%d')}"

from django.db import models
from apps.orders.models import Order


class Payment(models.Model):
    """
    Records every individual payment attempt (successful, failed, or pending)
    processed through Razorpay.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_CAPTURED = 'CAPTURED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CAPTURED, 'Captured'),
        (STATUS_FAILED, 'Failed'),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='payments',
        help_text="Order associated with this payment transaction"
    )
    razorpay_payment_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Payment ID issued by Razorpay (e.g. pay_P123456789)"
    )
    razorpay_signature = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Cryptographic payment signature verified via HMAC-SHA256"
    )
    payment_method = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Payment method used: upi, card, netbanking, etc."
    )
    amount_paise = models.PositiveBigIntegerField(
        help_text="Amount received in integer paise"
    )
    currency = models.CharField(
        max_length=3,
        default='INR',
        help_text="Currency code (INR)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text="Payment status"
    )
    error_code = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Error code returned by gateway on failure"
    )
    error_description = models.TextField(
        null=True,
        blank=True,
        help_text="Detailed error description"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"{self.razorpay_payment_id} ({self.get_status_display()}) - ₹{self.amount_paise / 100:.2f}"


class WebhookEvent(models.Model):
    """
    Stores incoming raw webhook events from Razorpay for auditing,
    replay protection, and asynchronous processing.
    """
    event_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique event ID from Razorpay webhook payload"
    )
    event_type = models.CharField(
        max_length=100,
        help_text="Event classification (e.g. payment.captured, payment.failed)"
    )
    payload = models.JSONField(
        help_text="Raw JSON payload received from Razorpay"
    )
    is_processed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this event has been successfully parsed and fulfilled"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when processing concluded"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webhook_events'
        ordering = ['-created_at']
        verbose_name = 'Webhook Event'
        verbose_name_plural = 'Webhook Events'

    def __str__(self):
        return f"{self.event_type} [{self.event_id}] (Processed: {self.is_processed})"

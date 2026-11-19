import uuid
from django.db import models
from django.conf import settings
from apps.products.models import Product


class Order(models.Model):
    """
    Transactional order record storing student purchase snapshots,
    itemized calculations, discount deductions, and 18% GST splits.
    All financial values are strictly represented in non-negative integer paise.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_PAID = 'PAID'
    STATUS_FAILED = 'FAILED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders',
        help_text="Student who placed this order"
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Human-readable unique order identifier (e.g. ORD-202611-0001)"
    )
    razorpay_order_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Razorpay Order ID (e.g. order_N123456789)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        help_text="Current transaction lifecycle status"
    )

    # Financial Breakdown (All in integer paise)
    gross_amount_paise = models.PositiveBigIntegerField(
        default=0,
        help_text="Sum of product regular prices before deductions"
    )
    upgrade_discount_paise = models.PositiveBigIntegerField(
        default=0,
        help_text="Prorated credit deducted from Subject Pack purchases"
    )
    coupon_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Promo coupon code applied to this order"
    )
    coupon_discount_paise = models.PositiveBigIntegerField(
        default=0,
        help_text="Promotional coupon discount amount deducted"
    )
    taxable_base_paise = models.PositiveBigIntegerField(
        default=0,
        help_text="Net base taxable amount: round(net_payable_paise / 1.18)"
    )
    gst_amount_paise = models.PositiveBigIntegerField(
        default=0,
        help_text="18% inclusive GST amount: net_payable_paise - taxable_base_paise"
    )
    net_payable_paise = models.PositiveBigIntegerField(
        default=0,
        help_text="Final payable amount charged to student"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()}) - ₹{self.net_payable_inr:.2f}"

    @property
    def net_payable_inr(self) -> float:
        return self.net_payable_paise / 100.0

    @property
    def taxable_base_inr(self) -> float:
        return self.taxable_base_paise / 100.0

    @property
    def gst_amount_inr(self) -> float:
        return self.gst_amount_paise / 100.0

    @classmethod
    def generate_order_number(cls) -> str:
        """Generates a unique order number."""
        return f"ORD-{uuid.uuid4().hex[:10].upper()}"


class OrderItem(models.Model):
    """
    Individual line item within an order capturing historical price snapshot,
    upgrade credits applied to this item, and net price charged.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Parent order containing this line item"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        help_text="Product purchased"
    )
    unit_price_paise = models.PositiveBigIntegerField(
        help_text="Standard unit price at the time of purchase"
    )
    upgrade_credit_paise = models.PositiveBigIntegerField(
        default=0,
        help_text="Upgrade credit applied to this specific line item"
    )
    net_price_paise = models.PositiveBigIntegerField(
        help_text="Net charged amount: max(0, unit_price_paise - upgrade_credit_paise)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.order.order_number} -> {self.product.title} (₹{self.net_price_paise / 100:.2f})"

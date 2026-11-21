import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.products.models import Product


class Coupon(models.Model):
    """
    Promotional coupon model supporting flat discounts (in integer paise)
    and percentage discounts (e.g. 10 for 10%) on order/cart subtotals.
    Enforces minimum order value, usage limits, and validity date windows.
    """
    DISCOUNT_TYPE_FLAT = 'FLAT'
    DISCOUNT_TYPE_PERCENTAGE = 'PERCENTAGE'

    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_TYPE_FLAT, 'Flat Discount (Paise)'),
        (DISCOUNT_TYPE_PERCENTAGE, 'Percentage Discount (%)'),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique promotional coupon code (e.g. FLAT50, DIWALI20)"
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default=DISCOUNT_TYPE_FLAT,
        help_text="Type of discount: FLAT (in paise) or PERCENTAGE (%)"
    )
    discount_value = models.PositiveBigIntegerField(
        help_text="Discount value: amount in paise for FLAT, or percentage number (e.g. 10 for 10%) for PERCENTAGE"
    )
    min_order_paise = models.PositiveBigIntegerField(
        default=0,
        help_text="Minimum cart/order subtotal in paise required to apply coupon"
    )
    max_discount_paise = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Optional maximum discount cap in paise (useful for percentage discounts)"
    )
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=100,
        help_text="Total maximum allowed redemptions across all users (null for unlimited)"
    )
    times_used = models.PositiveIntegerField(
        default=0,
        help_text="Current number of times this coupon has been successfully redeemed"
    )
    valid_from = models.DateTimeField(
        default=timezone.now,
        help_text="Start timestamp of coupon validity window"
    )
    valid_until = models.DateTimeField(
        help_text="Expiry timestamp of coupon validity window"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this coupon is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coupons'
        ordering = ['-created_at']
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'

    def __str__(self):
        if self.discount_type == self.DISCOUNT_TYPE_FLAT:
            return f"{self.code} (Flat ₹{self.discount_value / 100:.2f})"
        return f"{self.code} ({self.discount_value}% Off)"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.valid_until

    @property
    def is_usage_exhausted(self) -> bool:
        if self.usage_limit is None:
            return False
        return self.times_used >= self.usage_limit

    def calculate_discount(self, subtotal_paise: int) -> int:
        """
        Calculates discount in integer paise for a given cart/order subtotal.
        Returns 0 if subtotal < min_order_paise or coupon is invalid.
        Discount cannot exceed subtotal_paise.
        """
        if subtotal_paise <= 0 or subtotal_paise < self.min_order_paise:
            return 0

        if self.discount_type == self.DISCOUNT_TYPE_FLAT:
            discount = self.discount_value
        elif self.discount_type == self.DISCOUNT_TYPE_PERCENTAGE:
            # Round discount to nearest integer paise: round(subtotal * percent / 100)
            discount = round((subtotal_paise * self.discount_value) / 100)
        else:
            discount = 0

        # Apply maximum discount cap if specified
        if self.max_discount_paise is not None and self.max_discount_paise > 0:
            discount = min(discount, self.max_discount_paise)

        # Cap discount at subtotal (cannot make net payable negative)
        return min(discount, subtotal_paise)

    def validate_for_cart(self, subtotal_paise: int) -> tuple:
        """
        Validates coupon eligibility against current cart subtotal.
        Returns (is_valid: bool, error_message: str or None, discount_paise: int)
        """
        now = timezone.now()
        if not self.is_active:
            return False, "This coupon is inactive.", 0
        if self.valid_from and now < self.valid_from:
            return False, "This coupon is not yet valid.", 0
        if now > self.valid_until:
            return False, "This coupon has expired.", 0
        if self.is_usage_exhausted:
            return False, "This coupon has reached its maximum usage limit.", 0
        if subtotal_paise < self.min_order_paise:
            return False, f"Cart subtotal must be at least ₹{self.min_order_paise / 100:.2f} to apply this coupon.", 0

        discount = self.calculate_discount(subtotal_paise)
        return True, None, discount


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
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Promotional coupon applied to this order"
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
    def gross_amount_inr(self) -> float:
        return self.gross_amount_paise / 100.0

    @property
    def upgrade_discount_inr(self) -> float:
        return self.upgrade_discount_paise / 100.0

    @property
    def coupon_discount_inr(self) -> float:
        return self.coupon_discount_paise / 100.0

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

    @property
    def unit_price_inr(self) -> float:
        return self.unit_price_paise / 100.0

    @property
    def upgrade_credit_inr(self) -> float:
        return self.upgrade_credit_paise / 100.0

    @property
    def net_price_inr(self) -> float:
        return self.net_price_paise / 100.0

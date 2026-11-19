from django.db import models
from django.utils import timezone
from apps.catalog.models import Board, ClassLevel, Subject, Chapter


class Product(models.Model):
    """
    Commercial product representing content or access packages.
    Supports 6 distinct product types:
    - Chapter notes (single chapter, lifetime)
    - Subject pack (all chapters in subject, lifetime)
    - Monthly pass (all subjects in class, 30 days)
    - Annual pass (all subjects in class, 365 days)
    - Custom bundle (curated chapters/subjects, lifetime)
    - Free sample (preview chapter, lifetime, 0 paise)
    """
    PRODUCT_TYPE_CHAPTER_NOTES = 'CHAPTER_NOTES'
    PRODUCT_TYPE_SUBJECT_PACK = 'SUBJECT_PACK'
    PRODUCT_TYPE_MONTHLY_PASS = 'MONTHLY_PASS'
    PRODUCT_TYPE_ANNUAL_PASS = 'ANNUAL_PASS'
    PRODUCT_TYPE_BUNDLE = 'BUNDLE'
    PRODUCT_TYPE_FREE_SAMPLE = 'FREE_SAMPLE'

    PRODUCT_TYPE_CHOICES = [
        (PRODUCT_TYPE_CHAPTER_NOTES, 'Chapter Notes'),
        (PRODUCT_TYPE_SUBJECT_PACK, 'Subject Pack'),
        (PRODUCT_TYPE_MONTHLY_PASS, 'Monthly Class Pass'),
        (PRODUCT_TYPE_ANNUAL_PASS, 'Annual Class Pass'),
        (PRODUCT_TYPE_BUNDLE, 'Custom Bundle'),
        (PRODUCT_TYPE_FREE_SAMPLE, 'Free Sample'),
    ]

    title = models.CharField(max_length=200, help_text="Product display title")
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly identifier")
    product_type = models.CharField(
        max_length=30,
        choices=PRODUCT_TYPE_CHOICES,
        help_text="Classification defining access duration and scope"
    )
    description = models.TextField(blank=True, null=True, help_text="Product description and inclusions summary")

    # Relational hierarchy associations (nullable depending on product_type)
    board = models.ForeignKey(
        Board,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="Applicable board (for pass, subject pack, or chapter notes)"
    )
    academic_class = models.ForeignKey(
        ClassLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='class_id',
        related_name='products',
        help_text="Applicable class (for monthly/annual class passes)"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="Applicable subject (for subject packs)"
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        help_text="Applicable chapter (for chapter notes or free samples)"
    )

    is_active = models.BooleanField(default=True, help_text="Flag controlling public visibility")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.title} ({self.get_product_type_display()})"

    @property
    def current_price(self):
        """Returns the current active Price instance, or None."""
        if self.product_type == self.PRODUCT_TYPE_FREE_SAMPLE:
            return None
        return self.prices.filter(is_current=True).first()

    @property
    def current_price_paise(self) -> int:
        """Returns current price in integer paise (strictly 0 for free samples)."""
        if self.product_type == self.PRODUCT_TYPE_FREE_SAMPLE:
            return 0
        price_obj = self.current_price
        return price_obj.amount_paise if price_obj else 0

    @property
    def current_price_inr(self) -> float:
        """Helper returning price in standard rupees."""
        return self.current_price_paise / 100.0


class Price(models.Model):
    """
    Stores historical and current pricing for products.
    Money is strictly represented as a positive 64-bit integer in paise (1 INR = 100 paise).
    Floating-point representations are strictly forbidden for currency storage.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='prices',
        help_text="Product this price applies to"
    )
    amount_paise = models.PositiveBigIntegerField(
        help_text="Price in integer paise (e.g. 49900 paise = ₹499.00)"
    )
    currency = models.CharField(
        max_length=3,
        default='INR',
        help_text="ISO 4217 3-letter currency code"
    )
    valid_from = models.DateTimeField(
        default=timezone.now,
        help_text="Timestamp when this price becomes active"
    )
    valid_until = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Optional expiration timestamp for this price point"
    )
    is_current = models.BooleanField(
        default=True,
        help_text="Indicates whether this is the currently active price"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'prices'
        ordering = ['-valid_from']
        verbose_name = 'Price'
        verbose_name_plural = 'Prices'

    def __str__(self):
        return f"{self.product.title}: ₹{self.amount_paise / 100:.2f} ({self.amount_paise} paise)"


class BundleItem(models.Model):
    """
    Associates chapters or subjects with a Custom Bundle product.
    """
    TARGET_TYPE_CHAPTER = 'CHAPTER'
    TARGET_TYPE_SUBJECT = 'SUBJECT'
    TARGET_TYPE_CHOICES = [
        (TARGET_TYPE_CHAPTER, 'Chapter'),
        (TARGET_TYPE_SUBJECT, 'Subject'),
    ]

    bundle_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='bundle_items',
        help_text="The bundle product containing this item"
    )
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES)
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='bundle_inclusions'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='bundle_inclusions'
    )

    class Meta:
        db_table = 'bundle_items'
        verbose_name = 'Bundle Item'
        verbose_name_plural = 'Bundle Items'

    def __str__(self):
        item_name = self.chapter.title if self.chapter else (self.subject.name if self.subject else "Unknown")
        return f"Bundle [{self.bundle_product.title}] -> {self.target_type}: {item_name}"

import pytest
from apps.orders.gst import calculate_inclusive_gst, verify_gst_split_integrity
from apps.orders.models import Coupon
from apps.products.services import calculate_subject_pack_upgrade_credit
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.products.models import Product, Price
from apps.entitlements.models import Entitlement
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestPricingEngineAndGST:
    """
    Issue #50: Unit tests for pricing engine, upgrade credits, and 18% GST split.
    Test Scenarios:
    - Subject Pack upgrade credit with prior chapter purchases.
    - Upgrade price floored at 0 paise.
    - 18% inclusive GST split accuracy.
    - Coupon percentage and flat discount calculations.
    """

    def test_inclusive_gst_split_accuracy(self):
        """18% inclusive GST calculation across standard price points."""
        # ₹49.00 (4900 paise)
        split = calculate_inclusive_gst(4900)
        assert split['base_taxable_paise'] + split['total_gst_paise'] == 4900
        assert split['base_taxable_paise'] == 4153
        assert split['total_gst_paise'] == 747
        assert split['cgst_paise'] + split['sgst_paise'] == 747

        # Zero paise
        zero_split = calculate_inclusive_gst(0)
        assert zero_split['base_taxable_paise'] == 0
        assert zero_split['total_gst_paise'] == 0

        # Mathematical integrity test across 1,000 price points
        assert verify_gst_split_integrity(max_price_paise=100000, step=100) is True

    def test_coupon_flat_and_percentage_discount_calculations(self):
        """Validates coupon discount mathematics for flat and percentage coupons."""
        from django.utils import timezone
        from datetime import timedelta

        # Flat ₹50 discount (5000 paise)
        flat_coupon = Coupon.objects.create(
            code="FLAT50_TEST",
            discount_type=Coupon.DISCOUNT_TYPE_FLAT,
            discount_value=5000,
            min_order_paise=10000,
            valid_until=timezone.now() + timedelta(days=30)
        )
        assert flat_coupon.calculate_discount(15000) == 5000
        assert flat_coupon.calculate_discount(4000) == 0  # Below min order
        assert flat_coupon.calculate_discount(3000) == 0

        # Percentage 20% discount with max cap ₹100 (10000 paise)
        pct_coupon = Coupon.objects.create(
            code="PCT20_TEST",
            discount_type=Coupon.DISCOUNT_TYPE_PERCENTAGE,
            discount_value=20,
            min_order_paise=5000,
            max_discount_paise=10000,
            valid_until=timezone.now() + timedelta(days=30)
        )
        # 20% of 20000 is 4000 paise
        assert pct_coupon.calculate_discount(20000) == 4000
        # 20% of 60000 is 12000 paise -> capped at 10000 paise
        assert pct_coupon.calculate_discount(60000) == 10000

    def test_subject_pack_upgrade_credit_with_prior_chapter_purchases(self):
        """
        Subject Pack upgrade formula:
        price = max(0, Subject Pack Price - Sum of Amounts Paid for Owned Chapters)
        """
        user = User.objects.create_user(email="upgrade_test@example.com", password="Password123!")
        board = Board.objects.create(name="CBSE UP", slug="cbse-up")
        cls = ClassLevel.objects.create(board=board, name="Class 10", slug="c10-up")
        subj = Subject.objects.create(academic_class=cls, name="Mathematics", slug="math-up")
        ch1 = Chapter.objects.create(subject=subj, chapter_number=1, title="Real Numbers", slug="rn-up")
        ch2 = Chapter.objects.create(subject=subj, chapter_number=2, title="Polynomials", slug="poly-up")

        # Chapter 1 product priced at ₹49
        ch1_prod = Product.objects.create(
            title="Real Numbers Notes",
            slug="rn-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=ch1
        )
        Price.objects.create(product=ch1_prod, amount_paise=4900, is_current=True)

        # Subject pack priced at ₹199 (19900 paise)
        pack_prod = Product.objects.create(
            title="Class 10 Math Pack",
            slug="c10-math-pack-up",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=subj
        )
        Price.objects.create(product=pack_prod, amount_paise=19900, is_current=True)

        # Student owns Chapter 1
        Entitlement.objects.create(
            user=user,
            product_type='CHAPTER',
            scope_id=ch1.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        calc = calculate_subject_pack_upgrade_credit(user, pack_prod)
        assert calc['base_price_paise'] == 19900
        assert calc['upgrade_credit_paise'] == 4900
        assert calc['payable_price_paise'] == 15000
        assert calc['owned_chapters_count'] == 1

    def test_upgrade_price_floored_at_zero_paise(self):
        """When accumulated chapter purchases exceed pack price, final price is floored at 0 paise."""
        user = User.objects.create_user(email="floor_test@example.com", password="Password123!")
        board = Board.objects.create(name="CBSE Floor", slug="cbse-fl")
        cls = ClassLevel.objects.create(board=board, name="Class 10", slug="c10-fl")
        subj = Subject.objects.create(academic_class=cls, name="Science", slug="sci-fl")
        ch1 = Chapter.objects.create(subject=subj, chapter_number=1, title="Chem 1", slug="c1-fl")
        ch2 = Chapter.objects.create(subject=subj, chapter_number=2, title="Chem 2", slug="c2-fl")
        ch3 = Chapter.objects.create(subject=subj, chapter_number=3, title="Chem 3", slug="c3-fl")

        for ch in [ch1, ch2, ch3]:
            ch_p = Product.objects.create(
                title=f"{ch.title} Notes",
                slug=f"{ch.slug}-notes",
                product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
                chapter=ch
            )
            Price.objects.create(product=ch_p, amount_paise=4900, is_current=True)
            Entitlement.objects.create(
                user=user,
                product_type='CHAPTER',
                scope_id=ch.id,
                access_type='LIFETIME',
                status='ACTIVE'
            )

        # Pack priced at ₹99 (9900 paise)
        pack_prod = Product.objects.create(
            title="Class 10 Science Pack",
            slug="c10-sci-pack-fl",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=subj
        )
        Price.objects.create(product=pack_prod, amount_paise=9900, is_current=True)

        calc = calculate_subject_pack_upgrade_credit(user, pack_prod)
        assert calc['base_price_paise'] == 9900
        assert calc['upgrade_credit_paise'] == 9900  # Capped at base price
        assert calc['payable_price_paise'] == 0  # Strictly floored at 0 paise
        assert calc['payable_price_paise'] >= 0


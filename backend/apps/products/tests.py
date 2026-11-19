from django.test import TestCase
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from .models import Product, Price, BundleItem


class ProductAndPriceModelTests(TestCase):
    def setUp(self):
        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="mathematics")
        self.chapter = Chapter.objects.create(subject=self.subject, chapter_number=1, title="Real Numbers", slug="real-numbers")

    def test_chapter_notes_pricing_in_integer_paise(self):
        product = Product.objects.create(
            title="Class 10 Math Chapter 1 Notes",
            slug="class-10-math-ch1-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=self.chapter
        )
        # Price is ₹49.00 -> 4900 paise
        price = Price.objects.create(
            product=product,
            amount_paise=4900,
            currency="INR",
            is_current=True
        )

        self.assertEqual(product.current_price_paise, 4900)
        self.assertEqual(product.current_price_inr, 49.00)
        self.assertIsInstance(product.current_price_paise, int)
        self.assertEqual(str(price), "Class 10 Math Chapter 1 Notes: ₹49.00 (4900 paise)")

    def test_subject_pack_pricing(self):
        product = Product.objects.create(
            title="Class 10 Math Subject Pack",
            slug="class-10-math-subject-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            subject=self.subject
        )
        # Price ₹499.00 -> 49900 paise
        Price.objects.create(
            product=product,
            amount_paise=49900,
            currency="INR",
            is_current=True
        )

        self.assertEqual(product.current_price_paise, 49900)
        self.assertEqual(product.current_price_inr, 499.00)

    def test_monthly_and_annual_passes(self):
        monthly_pass = Product.objects.create(
            title="Class 10 Monthly Pass",
            slug="class-10-monthly-pass",
            product_type=Product.PRODUCT_TYPE_MONTHLY_PASS,
            academic_class=self.academic_class
        )
        Price.objects.create(product=monthly_pass, amount_paise=29900, is_current=True)
        self.assertEqual(monthly_pass.current_price_paise, 29900)

        annual_pass = Product.objects.create(
            title="Class 10 Annual Pass",
            slug="class-10-annual-pass",
            product_type=Product.PRODUCT_TYPE_ANNUAL_PASS,
            academic_class=self.academic_class
        )
        Price.objects.create(product=annual_pass, amount_paise=249900, is_current=True)
        self.assertEqual(annual_pass.current_price_paise, 249900)

    def test_free_sample_price_is_zero(self):
        sample = Product.objects.create(
            title="Free Sample Chapter 1",
            slug="free-sample-ch1",
            product_type=Product.PRODUCT_TYPE_FREE_SAMPLE,
            chapter=self.chapter
        )
        self.assertEqual(sample.current_price_paise, 0)
        self.assertEqual(sample.current_price_inr, 0.0)

    def test_custom_bundle_and_bundle_items(self):
        bundle = Product.objects.create(
            title="Math + Physics Special Bundle",
            slug="math-physics-bundle",
            product_type=Product.PRODUCT_TYPE_BUNDLE
        )
        Price.objects.create(product=bundle, amount_paise=69900, is_current=True)
        
        item = BundleItem.objects.create(
            bundle_product=bundle,
            target_type=BundleItem.TARGET_TYPE_SUBJECT,
            subject=self.subject
        )

        self.assertEqual(bundle.current_price_paise, 69900)
        self.assertEqual(bundle.bundle_items.count(), 1)
        self.assertIn("Bundle", str(item))

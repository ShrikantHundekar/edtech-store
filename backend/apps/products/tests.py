from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from .models import Product, Price, BundleItem
from .services import calculate_gst_breakdown


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


class ProductCatalogAPITests(APITestCase):
    def setUp(self):
        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.math = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="mathematics")
        self.science = Subject.objects.create(academic_class=self.academic_class, name="Science", slug="science")

        self.ch1 = Chapter.objects.create(subject=self.math, chapter_number=1, title="Real Numbers", slug="real-numbers", is_free_sample=True)
        self.ch2 = Chapter.objects.create(subject=self.math, chapter_number=2, title="Polynomials", slug="polynomials", is_free_sample=False)
        self.ch3 = Chapter.objects.create(subject=self.science, chapter_number=1, title="Chemical Reactions", slug="chemical-reactions")

        # 1. CHAPTER_NOTES (₹49 -> 4,900 paise)
        self.p_chapter = Product.objects.create(
            title="Math Chapter 2 Notes",
            slug="math-ch2-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            board=self.board,
            academic_class=self.academic_class,
            subject=self.math,
            chapter=self.ch2,
            is_active=True
        )
        Price.objects.create(product=self.p_chapter, amount_paise=4900, is_current=True)

        # 2. SUBJECT_PACK (₹499 -> 49,900 paise)
        self.p_subject = Product.objects.create(
            title="Class 10 Math Subject Pack",
            slug="class-10-math-pack",
            product_type=Product.PRODUCT_TYPE_SUBJECT_PACK,
            board=self.board,
            academic_class=self.academic_class,
            subject=self.math,
            is_active=True
        )
        Price.objects.create(product=self.p_subject, amount_paise=49900, is_current=True)

        # 3. MONTHLY_PASS (₹299 -> 29,900 paise, 30 days)
        self.p_monthly = Product.objects.create(
            title="Class 10 Monthly Pass",
            slug="class-10-monthly-pass",
            product_type=Product.PRODUCT_TYPE_MONTHLY_PASS,
            board=self.board,
            academic_class=self.academic_class,
            is_active=True
        )
        Price.objects.create(product=self.p_monthly, amount_paise=29900, is_current=True)

        # 4. ANNUAL_PASS (₹2,499 -> 249,900 paise, 365 days)
        self.p_annual = Product.objects.create(
            title="Class 10 Annual Pass",
            slug="class-10-annual-pass",
            product_type=Product.PRODUCT_TYPE_ANNUAL_PASS,
            board=self.board,
            academic_class=self.academic_class,
            is_active=True
        )
        Price.objects.create(product=self.p_annual, amount_paise=249900, is_current=True)

        # 5. BUNDLE (₹699 -> 69,900 paise)
        self.p_bundle = Product.objects.create(
            title="STEM Super Bundle",
            slug="stem-super-bundle",
            product_type=Product.PRODUCT_TYPE_BUNDLE,
            board=self.board,
            is_active=True
        )
        Price.objects.create(product=self.p_bundle, amount_paise=69900, is_current=True)
        BundleItem.objects.create(bundle_product=self.p_bundle, target_type='CHAPTER', chapter=self.ch2)
        BundleItem.objects.create(bundle_product=self.p_bundle, target_type='SUBJECT', subject=self.science)

        # 6. FREE_SAMPLE (₹0 -> 0 paise)
        self.p_free = Product.objects.create(
            title="Free Real Numbers Sample",
            slug="free-real-numbers-sample",
            product_type=Product.PRODUCT_TYPE_FREE_SAMPLE,
            board=self.board,
            academic_class=self.academic_class,
            subject=self.math,
            chapter=self.ch1,
            is_active=True
        )

        # Inactive product (should be hidden)
        self.p_inactive = Product.objects.create(
            title="Archived Old Course",
            slug="archived-old-course",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            is_active=False
        )
        Price.objects.create(product=self.p_inactive, amount_paise=1000, is_current=True)

    def test_list_products_returns_all_active_types(self):
        resp = self.client.get('/api/v1/products/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # 6 active products created, inactive is excluded
        self.assertEqual(len(resp.data), 6)
        slugs = [p['slug'] for p in resp.data]
        self.assertNotIn("archived-old-course", slugs)
        self.assertIn("math-ch2-notes", slugs)
        self.assertIn("class-10-math-pack", slugs)
        self.assertIn("class-10-monthly-pass", slugs)
        self.assertIn("class-10-annual-pass", slugs)
        self.assertIn("stem-super-bundle", slugs)
        self.assertIn("free-real-numbers-sample", slugs)

    def test_filter_products_by_type(self):
        resp = self.client.get('/api/v1/products/?product_type=SUBJECT_PACK')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['product_type'], 'SUBJECT_PACK')
        self.assertEqual(resp.data[0]['slug'], 'class-10-math-pack')

    def test_filter_products_by_class(self):
        resp = self.client.get(f'/api/v1/products/?class_id={self.academic_class.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 5 products are tied to class 10 (chapter, subject, monthly, annual, free sample)
        self.assertEqual(len(resp.data), 5)

    def test_chapter_notes_detail_and_gst_breakdown(self):
        resp = self.client.get(f'/api/v1/products/{self.p_chapter.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['title'], "Math Chapter 2 Notes")
        self.assertEqual(data['product_type'], "CHAPTER_NOTES")
        self.assertEqual(data['price_paise'], 4900)
        self.assertEqual(data['price_inr'], 49.00)
        self.assertEqual(data['access_duration'], "Lifetime")

        # Inclusions: Chapter 2
        self.assertEqual(len(data['inclusions']), 1)
        self.assertEqual(data['inclusions'][0]['id'], self.ch2.id)
        self.assertEqual(data['inclusions'][0]['title'], "Polynomials")

        # 18% inclusive GST split:
        # Base taxable = round(4900 / 1.18) = 4153
        # Total GST = 4900 - 4153 = 747
        # CGST = 374, SGST = 373
        gst = data['gst_breakdown']
        self.assertEqual(gst['price_inclusive_paise'], 4900)
        self.assertEqual(gst['base_taxable_paise'], 4153)
        self.assertEqual(gst['total_gst_paise'], 747)
        self.assertEqual(gst['cgst_paise'], 374)
        self.assertEqual(gst['sgst_paise'], 373)
        self.assertEqual(gst['cgst_paise'] + gst['sgst_paise'], gst['total_gst_paise'])
        self.assertEqual(gst['base_taxable_paise'] + gst['total_gst_paise'], 4900)

    def test_subject_pack_detail_and_inclusions(self):
        resp = self.client.get(f'/api/v1/products/{self.p_subject.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 49900)
        self.assertEqual(data['price_inr'], 499.00)
        self.assertEqual(data['access_duration'], "Lifetime")

        # Inclusions: chapters 1 and 2 under Math
        self.assertEqual(len(data['inclusions']), 2)
        ch_ids = [c['id'] for c in data['inclusions']]
        self.assertIn(self.ch1.id, ch_ids)
        self.assertIn(self.ch2.id, ch_ids)

        # 18% GST split matching specification exactly:
        # Base taxable = 42288 paise (₹422.88)
        # Total GST = 7612 paise (₹76.12)
        # CGST = 3806 paise (₹38.06)
        # SGST = 3806 paise (₹38.06)
        gst = data['gst_breakdown']
        self.assertEqual(gst['price_inclusive_paise'], 49900)
        self.assertEqual(gst['base_taxable_paise'], 42288)
        self.assertEqual(gst['total_gst_paise'], 7612)
        self.assertEqual(gst['cgst_paise'], 3806)
        self.assertEqual(gst['sgst_paise'], 3806)

    def test_monthly_pass_detail(self):
        resp = self.client.get(f'/api/v1/products/{self.p_monthly.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 29900)
        self.assertEqual(data['access_duration'], "30 Days")
        # Inclusions: list of subjects in class
        self.assertGreaterEqual(len(data['inclusions']), 2)

    def test_annual_pass_detail(self):
        resp = self.client.get(f'/api/v1/products/{self.p_annual.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 249900)
        self.assertEqual(data['access_duration'], "365 Days")

    def test_bundle_detail_and_inclusions(self):
        resp = self.client.get(f'/api/v1/products/{self.p_bundle.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 69900)
        self.assertEqual(data['access_duration'], "Lifetime")
        self.assertEqual(len(data['inclusions']), 2)
        types = [item['target_type'] for item in data['inclusions']]
        self.assertIn('CHAPTER', types)
        self.assertIn('SUBJECT', types)

    def test_free_sample_detail_zero_price(self):
        resp = self.client.get(f'/api/v1/products/{self.p_free.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data

        self.assertEqual(data['price_paise'], 0)
        self.assertEqual(data['price_inr'], 0.0)
        self.assertEqual(data['access_duration'], "Lifetime")
        self.assertEqual(data['gst_breakdown']['price_inclusive_paise'], 0)
        self.assertEqual(data['gst_breakdown']['total_gst_paise'], 0)

    def test_nonexistent_product_returns_404(self):
        resp = self.client.get('/api/v1/products/99999/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


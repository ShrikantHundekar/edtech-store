import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from apps.products.models import Product, Price
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment

User = get_user_model()

@pytest.mark.django_db
class TestOrderHistoryAndPrintableInvoice:
    @pytest.fixture
    def setup_order_data(self):
        board = Board.objects.create(name="CBSE Invoice", slug="cbse-inv")
        class_10 = ClassLevel.objects.create(name="Class 10 Inv", slug="class-10-inv", board=board)
        subject = Subject.objects.create(name="Science Inv", slug="science-inv", academic_class=class_10)
        chapter = Chapter.objects.create(title="Light Reflection Inv", subject=subject, chapter_number=1)

        product = Product.objects.create(
            title="Class 10 Science Notes",
            slug="class-10-science-notes",
            product_type=Product.PRODUCT_TYPE_CHAPTER_NOTES,
            chapter=chapter,
            subject=subject,
            academic_class=class_10,
            board=board,
            is_active=True,
        )
        Price.objects.create(
            product=product,
            amount_paise=4900,
            currency="INR",
            is_current=True,
        )

        student1 = User.objects.create_user(
            email="student1_inv@test.com",
            password="StrongPassword123!",
            full_name="Aarav Sharma",
            role="STUDENT"
        )
        student2 = User.objects.create_user(
            email="student2_inv@test.com",
            password="StrongPassword123!",
            full_name="Rohan Verma",
            role="STUDENT"
        )

        order = Order.objects.create(
            user=student1,
            order_number="ORD-TEST-INV-001",
            status=Order.STATUS_PAID,
            gross_amount_paise=4900,
            upgrade_discount_paise=0,
            coupon_discount_paise=0,
            taxable_base_paise=4153,
            gst_amount_paise=747,
            net_payable_paise=4900,
            razorpay_order_id="order_inv_12345",
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            unit_price_paise=4900,
            upgrade_credit_paise=0,
            net_price_paise=4900,
        )
        Payment.objects.create(
            order=order,
            razorpay_payment_id="pay_inv_capture_789",
            razorpay_signature="mock_signature_hex",
            payment_method="upi",
            amount_paise=4900,
            currency="INR",
            status=Payment.STATUS_CAPTURED,
        )

        return {
            "student1": student1,
            "student2": student2,
            "order": order,
            "product": product,
        }

    def test_unauthenticated_orders_access_returns_401(self):
        client = APIClient()
        response = client.get("/api/v1/orders/")
        assert response.status_code == 401

    def test_student_order_history_lists_past_orders(self, setup_order_data):
        client = APIClient()
        client.force_authenticate(user=setup_order_data["student1"])

        response = client.get("/api/v1/orders/")
        assert response.status_code == 200
        orders = response.data
        assert len(orders) == 1
        ord_data = orders[0]
        assert ord_data["order_number"] == "ORD-TEST-INV-001"
        assert ord_data["status"] == "PAID"
        assert ord_data["net_payable_inr"] == 49.0
        assert ord_data["razorpay_payment_id"] == "pay_inv_capture_789"
        assert ord_data["payment_method"] == "upi"
        assert "gst_breakdown" in ord_data
        assert ord_data["gst_breakdown"]["total_gst_inr"] == 7.47

    def test_printable_html_invoice_contains_gst_split_and_payment_id(self, setup_order_data):
        client = APIClient()
        client.force_authenticate(user=setup_order_data["student1"])

        order_id = setup_order_data["order"].id
        response = client.get(f"/api/v1/orders/{order_id}/invoice/")
        assert response.status_code == 200
        assert "text/html" in response["Content-Type"]

        html_text = response.content.decode("utf-8")
        assert "TAX INVOICE" in html_text
        assert "ORD-TEST-INV-001" in html_text
        assert "pay_inv_capture_789" in html_text
        assert "Aarav Sharma" in html_text
        assert "CGST (9.0%)" in html_text
        assert "SGST (9.0%)" in html_text
        assert "Total GST (18.0%)" in html_text
        assert "GSTIN: 27AABCE1234F1Z5" in html_text

    def test_unauthorized_user_cannot_access_other_student_invoice(self, setup_order_data):
        client = APIClient()
        client.force_authenticate(user=setup_order_data["student2"])

        order_id = setup_order_data["order"].id
        response = client.get(f"/api/v1/orders/{order_id}/invoice/")
        assert response.status_code == 403

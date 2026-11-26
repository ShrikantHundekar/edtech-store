from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from apps.products.models import Product
from apps.products.services import recalculate_cart_pricing
from .models import Order
from .serializers import OrderSerializer
from .services import validate_and_apply_coupon, create_order


class CouponApplyView(APIView):
    """
    POST /api/v1/coupons/apply/
    Validates promotional coupon code against cart items or cart subtotal.
    Returns calculated discount, resulting net payable amount, and 18% inclusive GST split.
    Rejects:
    - Non-existent coupon codes
    - Inactive coupons
    - Expired coupons
    - Coupons exceeding usage limits
    - Orders below the required minimum cart amount
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        code = request.data.get('code')
        if not code:
            return Response(
                {"valid": False, "error": "Coupon code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        subtotal_paise = 0
        raw_items = request.data.get('items')

        if raw_items:
            # Recompute server-authoritative subtotal from database
            product_ids = []
            for item in raw_items:
                if isinstance(item, dict):
                    pid = item.get('product_id') or item.get('id')
                    if pid:
                        product_ids.append(pid)
                elif isinstance(item, (int, str)):
                    try:
                        product_ids.append(int(item))
                    except ValueError:
                        pass

            products = list(Product.objects.filter(id__in=product_ids).select_related(
                'academic_class', 'subject', 'chapter'
            ).prefetch_related('prices'))

            product_map = {p.id: p for p in products}
            ordered_products = [product_map[pid] for pid in product_ids if pid in product_map]
            user = request.user if request.user.is_authenticated else None
            cart_data = recalculate_cart_pricing(user, ordered_products)
            subtotal_paise = cart_data['pricing']['subtotal_paise']
        else:
            # Direct subtotal submitted
            subtotal_paise = request.data.get('cart_subtotal_paise') or request.data.get('subtotal_paise') or 0
            try:
                subtotal_paise = int(subtotal_paise)
            except (ValueError, TypeError):
                subtotal_paise = 0

        user = request.user if request.user.is_authenticated else None
        result = validate_and_apply_coupon(code, subtotal_paise, user=user)

        if not result['valid']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class OrderCreateView(APIView):
    """
    POST /api/v1/orders/create/
    Server-authoritative Order creation endpoint:
    - Strictly rejects untrusted client prices; recalculates everything from the database.
    - Validates cart items against user ownership and overlapping purchase rules.
    - Applies upgrade credit for Subject Packs based on user's past purchases.
    - Validates promotional coupon against the recalculation subtotal.
    - Computes 18% inclusive GST split (base taxable + GST amount).
    - Initializes the Order record with status 'PENDING'.
    - Creates corresponding itemized OrderItem snapshots.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        raw_items = request.data.get('items', [])
        coupon_code = request.data.get('coupon_code') or request.data.get('coupon')

        try:
            order = create_order(request.user, raw_items, coupon_code=coupon_code)
        except ValidationError as err:
            return Response(err.detail, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    """
    GET /api/v1/orders/
    Returns list of orders for the authenticated student.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'ADMIN' or user.is_staff or user.is_superuser:
            return Order.objects.all().select_related('user', 'coupon').prefetch_related('items__product', 'payments').order_by('-created_at')
        return Order.objects.filter(user=user).select_related('coupon').prefetch_related('items__product', 'payments').order_by('-created_at')


class OrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/orders/{id}/
    Returns details of a specific order.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == 'ADMIN' or user.is_staff or user.is_superuser:
            return Order.objects.all().select_related('user', 'coupon').prefetch_related('items__product', 'payments')
        return Order.objects.filter(user=user).select_related('coupon').prefetch_related('items__product', 'payments')


class OrderInvoiceView(APIView):
    """
    GET /api/v1/orders/{id}/invoice/
    Returns printable tax invoice HTML for the order.
    Enforces student ownership or admin privileges.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        from django.http import HttpResponse
        from .gst import calculate_gst_breakdown

        order = get_object_or_404(
            Order.objects.select_related('user', 'coupon').prefetch_related('items__product', 'payments'),
            id=pk
        )

        # Access check
        if order.user != request.user and not (request.user.is_staff or getattr(request.user, 'role', None) == 'ADMIN'):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        # Payment details
        payment = order.payments.filter(status='CAPTURED').first()
        payment_id = payment.razorpay_payment_id if payment else (order.razorpay_order_id or 'N/A')
        payment_method = (payment.payment_method if payment else 'Razorpay').upper()

        gst = calculate_gst_breakdown(order.net_payable_paise)
        cgst_inr = gst['cgst_inr']
        sgst_inr = gst['sgst_inr']
        taxable_inr = gst['base_taxable_inr']
        total_gst_inr = gst['total_gst_inr']

        # Format items rows
        items_rows = ""
        for idx, item in enumerate(order.items.all(), 1):
            prod_name = item.product.title if item.product else 'Digital Study Notes'
            items_rows += f"""
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: center;">{idx}</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">
                <strong>{prod_name}</strong>
                <div style="font-size: 11px; color: #64748b;">SAC Code: 998431 (Online Educational Content)</div>
              </td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right;">₹{item.unit_price_inr:.2f}</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; color: #16a34a;">-₹{item.upgrade_credit_inr:.2f}</td>
              <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold;">₹{item.net_price_inr:.2f}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Tax Invoice - {order.order_number}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      margin: 0;
      padding: 30px;
      background: #f8fafc;
    }}
    .invoice-card {{
      max-width: 800px;
      margin: 0 auto;
      background: #ffffff;
      padding: 40px;
      border-radius: 16px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      border: 1px solid #e2e8f0;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      border-bottom: 2px solid #4f46e5;
      padding-bottom: 20px;
      margin-bottom: 25px;
    }}
    .brand {{
      font-size: 24px;
      font-weight: 900;
      color: #4f46e5;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      font-size: 11px;
      font-weight: bold;
      border-radius: 6px;
      text-transform: uppercase;
    }}
    .badge-paid {{
      background: #dcfce7;
      color: #166534;
    }}
    .grid {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 25px;
      font-size: 13px;
      line-height: 1.6;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      margin-bottom: 25px;
    }}
    th {{
      background: #f1f5f9;
      padding: 10px;
      text-align: left;
      font-weight: bold;
      border-bottom: 2px solid #cbd5e1;
    }}
    .summary-table {{
      width: 320px;
      margin-left: auto;
      font-size: 13px;
    }}
    .summary-table td {{
      padding: 6px 10px;
    }}
    .print-btn {{
      background: #4f46e5;
      color: #ffffff;
      border: none;
      padding: 10px 20px;
      font-size: 14px;
      font-weight: bold;
      border-radius: 8px;
      cursor: pointer;
      margin-bottom: 20px;
    }}
    @media print {{
      body {{ background: #ffffff; padding: 0; }}
      .invoice-card {{ box-shadow: none; border: none; padding: 0; }}
      .no-print {{ display: none !important; }}
    }}
  </style>
</head>
<body>
  <div style="max-width: 800px; margin: 0 auto;" class="no-print">
    <button class="print-btn" onclick="window.print()">🖨️ Print Tax Invoice</button>
  </div>

  <div class="invoice-card">
    <div class="header">
      <div>
        <div class="brand">🎓 EdTech Store</div>
        <div style="font-size: 12px; color: #64748b; margin-top: 4px;">CBSE Digital Notes & Educational Pass Platform</div>
        <div style="font-size: 11px; color: #64748b;">GSTIN: 27AABCE1234F1Z5 | PAN: AABCE1234F</div>
      </div>
      <div style="text-align: right;">
        <span class="badge badge-paid">{order.status}</span>
        <h2 style="margin: 8px 0 2px 0; font-size: 20px; color: #0f172a;">TAX INVOICE</h2>
        <div style="font-size: 12px; font-weight: bold; color: #4f46e5;">#{order.order_number}</div>
        <div style="font-size: 11px; color: #64748b;">Date: {order.created_at.strftime('%d %B %Y')}</div>
      </div>
    </div>

    <div class="grid">
      <div>
        <strong style="color: #475569; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em;">Billed To (Student)</strong>
        <div style="font-weight: bold; font-size: 14px; margin-top: 2px;">{order.user.full_name or 'Student'}</div>
        <div>Email: {order.user.email}</div>
        <div>Account Role: {order.user.role}</div>
      </div>
      <div style="text-align: right;">
        <strong style="color: #475569; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em;">Payment Information</strong>
        <div>Payment Gateway: <strong>Razorpay Test Mode</strong></div>
        <div>Razorpay Payment ID: <code style="font-size: 12px; background: #f1f5f9; padding: 2px 5px; border-radius: 4px;">{payment_id}</code></div>
        <div>Method: <strong>{payment_method}</strong></div>
      </div>
    </div>

    <table>
      <thead>
        <tr>
          <th style="width: 40px; text-align: center;">#</th>
          <th>Description of Supply</th>
          <th style="width: 100px; text-align: right;">Unit Price</th>
          <th style="width: 110px; text-align: right;">Upgrade Credit</th>
          <th style="width: 100px; text-align: right;">Net Amount</th>
        </tr>
      </thead>
      <tbody>
        {items_rows}
      </tbody>
    </table>

    <table class="summary-table">
      <tr>
        <td>Gross Subtotal:</td>
        <td style="text-align: right; font-weight: bold;">₹{order.gross_amount_inr:.2f}</td>
      </tr>
      {"<tr><td>Upgrade Credits:</td><td style='text-align: right; color: #16a34a; font-weight: bold;'>-₹" + f"{order.upgrade_discount_inr:.2f}" + "</td></tr>" if order.upgrade_discount_paise > 0 else ""}
      {"<tr><td>Promotional Discount (" + (order.coupon_code or '') + "):</td><td style='text-align: right; color: #16a34a; font-weight: bold;'>-₹" + f"{order.coupon_discount_inr:.2f}" + "</td></tr>" if order.coupon_discount_paise > 0 else ""}
      <tr style="border-top: 1px solid #e2e8f0;">
        <td>Taxable Base Value:</td>
        <td style="text-align: right; font-weight: bold;">₹{taxable_inr:.2f}</td>
      </tr>
      <tr>
        <td>CGST (9.0%):</td>
        <td style="text-align: right;">₹{cgst_inr:.2f}</td>
      </tr>
      <tr>
        <td>SGST (9.0%):</td>
        <td style="text-align: right;">₹{sgst_inr:.2f}</td>
      </tr>
      <tr style="font-weight: bold; color: #475569;">
        <td>Total GST (18.0%):</td>
        <td style="text-align: right;">₹{total_gst_inr:.2f}</td>
      </tr>
      <tr style="border-top: 2px solid #0f172a; font-size: 15px;">
        <td style="font-weight: 900; color: #0f172a;">Total Amount Paid:</td>
        <td style="text-align: right; font-weight: 900; color: #4f46e5;">₹{order.net_payable_inr:.2f}</td>
      </tr>
    </table>

    <div style="margin-top: 35px; padding-top: 20px; border-top: 1px dashed #cbd5e1; font-size: 11px; color: #64748b; line-height: 1.5;">
      <strong>Terms & Conditions:</strong><br>
      1. This is a computer-generated GST tax invoice for supply of digital educational study notes and passes.<br>
      2. 18% GST (CGST 9% + SGST 9%) has been inclusive in the supply price as per Indian GST laws.<br>
      3. For queries or entitlement support, contact support@edtechstore.local with Order #{order.order_number}.
    </div>
  </div>
</body>
</html>
"""
        return HttpResponse(html_content, content_type='text/html')



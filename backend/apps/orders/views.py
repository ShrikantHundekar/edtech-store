from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.products.models import Product
from apps.products.services import recalculate_cart_pricing
from .services import validate_and_apply_coupon


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

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Product
from .serializers import ProductSerializer
from .services import check_product_purchase_eligibility, validate_cart_items_eligibility


class ProductListView(generics.ListAPIView):
    """
    GET /api/v1/products/
    Returns list of active products supporting all 6 types:
    Chapter notes, Subject packs, Monthly passes, Annual passes, Bundles, and Free samples.
    
    Optional filters:
    - ?product_type=...
    - ?board_id=...
    - ?class_id=...
    - ?subject_id=...
    - ?chapter_id=...
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related(
            'board', 'academic_class', 'subject', 'chapter'
        ).prefetch_related(
            'prices',
            'bundle_items__chapter__subject',
            'bundle_items__subject',
        ).order_by('-created_at')

        product_type = self.request.query_params.get('product_type')
        if product_type:
            qs = qs.filter(product_type=product_type.upper())

        board_id = self.request.query_params.get('board_id')
        if board_id:
            qs = qs.filter(board_id=board_id)

        class_id = self.request.query_params.get('class_id')
        if class_id:
            qs = qs.filter(academic_class_id=class_id)

        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        chapter_id = self.request.query_params.get('chapter_id')
        if chapter_id:
            qs = qs.filter(chapter_id=chapter_id)

        return qs


class ProductDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/products/{id}/
    Returns detailed view for a single product, including:
    - Inclusions list
    - Current price in integer paise
    - 18% inclusive GST split breakdown
    - Access duration
    - Dynamic purchase state for user: BUY, OWNED, UPGRADE, UNLOCKED_VIA_PASS
    """
    queryset = Product.objects.filter(is_active=True).select_related(
        'board', 'academic_class', 'subject', 'chapter'
    ).prefetch_related(
        'prices',
        'bundle_items__chapter__subject',
        'bundle_items__subject',
    )
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]


class ProductOwnershipView(APIView):
    """
    GET /api/v1/products/{id}/ownership/
    Returns dynamic purchase state for the requesting user:
    - 'BUY': User does not own the product and has no overlapping entitlements.
    - 'OWNED': User already holds an active entitlement for this product or parent pack.
    - 'UPGRADE': User owns individual chapters and can upgrade to the Subject Pack with discount.
    - 'UNLOCKED_VIA_PASS': Content is unlocked via an active Class Pass.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk, *args, **kwargs):
        product = get_object_or_404(
            Product.objects.select_related('academic_class', 'subject', 'chapter'),
            id=pk
        )
        user = request.user if request.user.is_authenticated else None
        can_purchase, purchase_state, reason = check_product_purchase_eligibility(user, product)

        return Response(
            {
                "product_id": product.id,
                "title": product.title,
                "product_type": product.product_type,
                "purchase_state": purchase_state,
                "can_purchase": can_purchase,
                "reason": reason,
            },
            status=status.HTTP_200_OK
        )


class CartValidateEligibilityView(APIView):
    """
    POST /api/v1/cart/validate/
    POST /api/v1/products/validate-cart/
    Validates cart items against user ownership and overlapping purchase rules:
    - Rejects items already owned by user.
    - Rejects items already unlocked by an active Class Pass.
    - Rejects intra-cart overlaps (e.g. buying both Subject Pack and a Chapter in that subject).
    - Rejects intra-cart overlaps (e.g. buying both Class Pass and a Subject/Chapter in that class).
    - Rejects duplicate items.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        raw_items = request.data.get('items', [])
        if not raw_items:
            return Response(
                {"valid": False, "errors": ["Cart is empty. Please provide at least one product item."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract product IDs (supports either list of IDs [1, 2] or list of dicts [{"product_id": 1}])
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

        if not product_ids:
            return Response(
                {"valid": False, "errors": ["No valid product IDs found in the items list."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        products = list(Product.objects.filter(id__in=product_ids).select_related(
            'academic_class', 'subject', 'chapter'
        ))

        found_ids = {p.id for p in products}
        missing_ids = [pid for pid in product_ids if pid not in found_ids]
        if missing_ids:
            return Response(
                {"valid": False, "errors": [f"Product ID {pid} does not exist." for pid in missing_ids]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Map back to preserve order / duplicate detection
        product_map = {p.id: p for p in products}
        ordered_products = [product_map[pid] for pid in product_ids]

        is_valid, errors = validate_cart_items_eligibility(request.user, ordered_products)
        if not is_valid:
            return Response(
                {
                    "valid": False,
                    "error": "Overlapping or ineligible items detected in cart.",
                    "errors": errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "valid": True,
                "message": "All items in cart are valid and eligible for purchase.",
                "items_count": len(ordered_products)
            },
            status=status.HTTP_200_OK
        )

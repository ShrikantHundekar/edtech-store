from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Prefetch
from apps.accounts.permissions import IsAdminRole
from .models import Product, Price, BundleItem
from .admin_serializers import (
    AdminProductSerializer,
    AdminPriceSerializer,
    AdminBundleItemSerializer,
)


class AdminProductViewSet(viewsets.ModelViewSet):
    """
    Admin ViewSet for Product and Pricing Configuration.
    Allows administrators to:
    - List and filter all products (including inactive)
    - Create products across all 6 product types with associated catalog scopes
    - Update metadata, scopes, and prices in paise
    - Add, list, and remove custom bundle items
    - Delete products
    """
    permission_classes = [IsAdminRole]
    serializer_class = AdminProductSerializer

    def get_queryset(self):
        return Product.objects.select_related(
            'board', 'academic_class', 'subject', 'chapter'
        ).prefetch_related(
            'prices',
            'bundle_items__chapter__subject',
            'bundle_items__subject',
        ).order_by('-created_at')

    @action(detail=True, methods=['get', 'post'], url_path='prices')
    def prices(self, request, pk=None):
        """
        GET /api/v1/admin/products/{id}/prices/ - list price history
        POST /api/v1/admin/products/{id}/prices/ - create a new price point
        """
        product = self.get_object()
        if request.method == 'GET':
            prices = product.prices.all().order_by('-valid_from')
            serializer = AdminPriceSerializer(prices, many=True)
            return Response(serializer.data)

        # POST new price
        amount_paise = request.data.get('amount_paise')
        if amount_paise is None:
            return Response({"error": "amount_paise is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount_paise = int(amount_paise)
            if amount_paise < 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response({"error": "amount_paise must be a non-negative integer."}, status=status.HTTP_400_BAD_REQUEST)

        # Deactivate previous active prices if is_current is true
        is_current = request.data.get('is_current', True)
        if is_current:
            product.prices.filter(is_current=True).update(is_current=False)

        price = Price.objects.create(
            product=product,
            amount_paise=amount_paise,
            is_current=is_current,
        )
        serializer = AdminPriceSerializer(price)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], url_path='bundle-items')
    def bundle_items(self, request, pk=None):
        """
        GET /api/v1/admin/products/{id}/bundle-items/ - list items in bundle
        POST /api/v1/admin/products/{id}/bundle-items/ - add item to bundle
        """
        product = self.get_object()
        if product.product_type != Product.PRODUCT_TYPE_BUNDLE:
            return Response({"error": "Bundle items can only be managed for BUNDLE products."}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'GET':
            items = product.bundle_items.select_related('chapter__subject', 'subject').all()
            serializer = AdminBundleItemSerializer(items, many=True)
            return Response(serializer.data)

        target_type = request.data.get('target_type')
        chapter_id = request.data.get('chapter')
        subject_id = request.data.get('subject')

        if target_type == BundleItem.TARGET_TYPE_CHAPTER and not chapter_id:
            return Response({"error": "chapter ID is required for CHAPTER bundle item."}, status=status.HTTP_400_BAD_REQUEST)
        elif target_type == BundleItem.TARGET_TYPE_SUBJECT and not subject_id:
            return Response({"error": "subject ID is required for SUBJECT bundle item."}, status=status.HTTP_400_BAD_REQUEST)

        bundle_item = BundleItem.objects.create(
            bundle_product=product,
            target_type=target_type,
            chapter_id=chapter_id,
            subject_id=subject_id,
        )
        serializer = AdminBundleItemSerializer(bundle_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='bundle-items/(?P<item_id>[^/.]+)')
    def remove_bundle_item(self, request, pk=None, item_id=None):
        product = self.get_object()
        item = product.bundle_items.filter(id=item_id).first()
        if not item:
            return Response({"error": "Bundle item not found."}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

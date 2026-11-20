from rest_framework import generics, permissions
from .models import Product
from .serializers import ProductSerializer


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

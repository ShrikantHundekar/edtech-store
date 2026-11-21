from django.urls import path
from .views import (
    ProductListView,
    ProductDetailView,
    ProductOwnershipView,
    ProductCalculatePriceView,
    CartValidateEligibilityView,
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('validate-cart/', CartValidateEligibilityView.as_view(), name='product_validate_cart'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('<int:pk>/ownership/', ProductOwnershipView.as_view(), name='product_ownership'),
    path('<int:pk>/calculate-price/', ProductCalculatePriceView.as_view(), name='product_calculate_price'),
]

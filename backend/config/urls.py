"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from apps.products.views import CartValidateEligibilityView


def block_direct_media_access(request, *args, **kwargs):
    """
    Explicit security barrier: disallows direct static file fetching of study materials.
    All notes must be streamed via /api/v1/materials/{id}/stream/ after entitlement validation.
    """
    return JsonResponse(
        {
            "error": "Forbidden: Direct static URL access to study notes is disallowed. Please use the authorized streaming endpoint: /api/v1/materials/{id}/stream/"
        },
        status=403
    )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/admin/', include('apps.catalog.admin_urls')),
    path('api/v1/catalog/', include('apps.catalog.public_urls')),
    path('api/v1/materials/', include('apps.catalog.material_urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/cart/validate/', CartValidateEligibilityView.as_view(), name='cart_validate'),
    path('api/v1/coupons/', include('apps.orders.coupon_urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    # Explicit security barriers: Restrict raw direct access to notes
    path('media/notes/<path:path>', block_direct_media_access, name='block_direct_media_notes'),
    path('media/materials/<path:path>', block_direct_media_access, name='block_direct_media_materials'),
    path('protected_media/<path:path>', block_direct_media_access, name='block_direct_protected_media'),
]

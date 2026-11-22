from django.urls import path
from .views import (
    AdminManualGrantEntitlementView,
    AdminManualRevokeEntitlementView,
    AdminManualAccessLogListView,
    AdminEntitlementListView,
)

urlpatterns = [
    path('', AdminEntitlementListView.as_view(), name='admin_entitlement_list'),
    path('grant/', AdminManualGrantEntitlementView.as_view(), name='admin_entitlement_grant'),
    path('<int:pk>/revoke/', AdminManualRevokeEntitlementView.as_view(), name='admin_entitlement_revoke'),
    path('logs/', AdminManualAccessLogListView.as_view(), name='admin_manual_access_logs'),
]

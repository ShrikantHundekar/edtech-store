from django.contrib import admin
from .models import Entitlement, ManualAccessLog


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product_type', 'scope_id', 'access_type', 'status', 'valid_until', 'created_at')
    list_filter = ('product_type', 'access_type', 'status')
    search_fields = ('user__email', 'scope_id')


@admin.register(ManualAccessLog)
class ManualAccessLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'admin', 'student', 'action', 'entitlement', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('admin__email', 'student__email', 'reason')

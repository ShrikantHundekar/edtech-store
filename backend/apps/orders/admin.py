from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'unit_price_paise', 'upgrade_credit_paise', 'net_price_paise', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'status',
        'get_net_payable_display',
        'razorpay_order_id',
        'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'razorpay_order_id', 'user__email', 'user__username')
    readonly_fields = (
        'order_number',
        'created_at',
        'updated_at'
    )
    inlines = [OrderItemInline]

    def get_net_payable_display(self, obj):
        return f"₹{obj.net_payable_inr:.2f}"
    get_net_payable_display.short_description = 'Net Payable'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'unit_price_paise', 'net_price_paise', 'created_at')
    list_filter = ('product__product_type',)
    search_fields = ('order__order_number', 'product__title')

from django.contrib import admin
from .models import Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'razorpay_payment_id',
        'order',
        'get_amount_display',
        'payment_method',
        'status',
        'created_at'
    )
    list_filter = ('status', 'payment_method', 'currency', 'created_at')
    search_fields = ('razorpay_payment_id', 'order__order_number', 'error_code')
    readonly_fields = ('created_at', 'updated_at')

    def get_amount_display(self, obj):
        return f"₹{obj.amount_paise / 100:.2f}"
    get_amount_display.short_description = 'Amount (INR)'


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'event_type', 'is_processed', 'processed_at', 'created_at')
    list_filter = ('event_type', 'is_processed', 'created_at')
    search_fields = ('event_id', 'event_type')
    readonly_fields = ('event_id', 'event_type', 'payload', 'created_at')

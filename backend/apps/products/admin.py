from django.contrib import admin
from .models import Product, Price, BundleItem


class PriceInline(admin.TabularInline):
    model = Price
    extra = 1
    fields = ('amount_paise', 'currency', 'valid_from', 'valid_until', 'is_current')


class BundleItemInline(admin.TabularInline):
    model = BundleItem
    extra = 1
    fields = ('target_type', 'subject', 'chapter')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'product_type', 'get_price_display', 'is_active', 'created_at')
    list_filter = ('product_type', 'is_active', 'board', 'academic_class')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PriceInline, BundleItemInline]

    def get_price_display(self, obj):
        return f"₹{obj.current_price_inr:.2f}"
    get_price_display.short_description = 'Current Price'


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('product', 'amount_paise', 'get_inr_display', 'currency', 'is_current', 'valid_from')
    list_filter = ('is_current', 'currency')
    search_fields = ('product__title',)

    def get_inr_display(self, obj):
        return f"₹{obj.amount_paise / 100:.2f}"
    get_inr_display.short_description = 'Amount (INR)'


@admin.register(BundleItem)
class BundleItemAdmin(admin.ModelAdmin):
    list_display = ('bundle_product', 'target_type', 'subject', 'chapter')
    list_filter = ('target_type',)

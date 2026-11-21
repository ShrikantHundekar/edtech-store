from rest_framework import serializers
from .models import Order, OrderItem, Coupon
from apps.products.models import Product


class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_type = serializers.CharField(source='product.product_type', read_only=True)
    unit_price_inr = serializers.FloatField(read_only=True)
    upgrade_credit_inr = serializers.FloatField(read_only=True)
    net_price_inr = serializers.FloatField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_title',
            'product_type',
            'unit_price_paise',
            'unit_price_inr',
            'upgrade_credit_paise',
            'upgrade_credit_inr',
            'net_price_paise',
            'net_price_inr',
            'created_at',
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    gross_amount_inr = serializers.FloatField(read_only=True)
    upgrade_discount_inr = serializers.FloatField(read_only=True)
    coupon_discount_inr = serializers.FloatField(read_only=True)
    taxable_base_inr = serializers.FloatField(read_only=True)
    gst_amount_inr = serializers.FloatField(read_only=True)
    net_payable_inr = serializers.FloatField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'user',
            'status',
            'gross_amount_paise',
            'gross_amount_inr',
            'upgrade_discount_paise',
            'upgrade_discount_inr',
            'coupon',
            'coupon_code',
            'coupon_discount_paise',
            'coupon_discount_inr',
            'taxable_base_paise',
            'taxable_base_inr',
            'gst_amount_paise',
            'gst_amount_inr',
            'net_payable_paise',
            'net_payable_inr',
            'razorpay_order_id',
            'items',
            'created_at',
            'updated_at',
        ]

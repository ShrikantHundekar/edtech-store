from django.conf import settings
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
    amount_paise = serializers.IntegerField(source='net_payable_paise', read_only=True)
    currency = serializers.CharField(default='INR', read_only=True)
    razorpay_key_id = serializers.SerializerMethodField()
    razorpay_payment_id = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source='user.full_name', read_only=True)
    customer_email = serializers.EmailField(source='user.email', read_only=True)
    gst_breakdown = serializers.SerializerMethodField()

    def get_razorpay_key_id(self, obj):
        # Return Razorpay key for frontend Checkout modal integration
        return getattr(settings, 'RAZORPAY_KEY_ID', '')

    def get_razorpay_payment_id(self, obj):
        # Return latest captured payment ID
        payment = obj.payments.filter(status='CAPTURED').first()
        if not payment:
            payment = obj.payments.order_by('-created_at').first()
        return payment.razorpay_payment_id if payment else None

    def get_payment_method(self, obj):
        payment = obj.payments.filter(status='CAPTURED').first()
        if not payment:
            payment = obj.payments.order_by('-created_at').first()
        return payment.payment_method if payment else None

    def get_gst_breakdown(self, obj):
        from .gst import calculate_gst_breakdown
        return calculate_gst_breakdown(obj.net_payable_paise)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'user',
            'customer_name',
            'customer_email',
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
            'amount_paise',
            'currency',
            'razorpay_order_id',
            'razorpay_key_id',
            'razorpay_payment_id',
            'payment_method',
            'gst_breakdown',
            'items',
            'created_at',
            'updated_at',
        ]

from rest_framework import serializers
from .models import Product, Price, BundleItem
from .services import check_product_purchase_eligibility


class PriceSerializer(serializers.ModelSerializer):
    amount_inr = serializers.SerializerMethodField()

    class Meta:
        model = Price
        fields = (
            'id',
            'amount_paise',
            'currency',
            'valid_from',
            'valid_until',
            'is_current',
            'amount_inr',
        )

    def get_amount_inr(self, obj):
        return obj.amount_paise / 100.0


class ProductSerializer(serializers.ModelSerializer):
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    board_name = serializers.CharField(source='board.name', read_only=True)
    class_name = serializers.CharField(source='academic_class.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)

    price_paise = serializers.IntegerField(source='current_price_paise', read_only=True)
    price_inr = serializers.FloatField(source='current_price_inr', read_only=True)
    access_duration = serializers.CharField(read_only=True)
    pass_duration_days = serializers.IntegerField(read_only=True)
    gst_breakdown = serializers.DictField(read_only=True)
    inclusions = serializers.SerializerMethodField()
    purchase_state = serializers.SerializerMethodField()
    can_purchase = serializers.SerializerMethodField()
    purchase_state_reason = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id',
            'title',
            'slug',
            'product_type',
            'product_type_display',
            'description',
            'board',
            'board_name',
            'academic_class',
            'class_name',
            'subject',
            'subject_name',
            'chapter',
            'chapter_title',
            'is_active',
            'price_paise',
            'price_inr',
            'access_duration',
            'pass_duration_days',
            'gst_breakdown',
            'inclusions',
            'purchase_state',
            'can_purchase',
            'purchase_state_reason',
            'created_at',
            'updated_at',
        )

    def _get_eligibility(self, obj):
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else None
        return check_product_purchase_eligibility(user, obj)

    def get_inclusions(self, obj):
        return obj.get_inclusions()

    def get_purchase_state(self, obj):
        _, state, _ = self._get_eligibility(obj)
        return state

    def get_can_purchase(self, obj):
        can_buy, _, _ = self._get_eligibility(obj)
        return can_buy

    def get_purchase_state_reason(self, obj):
        _, _, reason = self._get_eligibility(obj)
        return reason


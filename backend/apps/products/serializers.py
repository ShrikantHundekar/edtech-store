from rest_framework import serializers
from .models import Product, Price, BundleItem


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
    gst_breakdown = serializers.DictField(read_only=True)
    inclusions = serializers.SerializerMethodField()

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
            'gst_breakdown',
            'inclusions',
            'created_at',
            'updated_at',
        )

    def get_inclusions(self, obj):
        return obj.get_inclusions()

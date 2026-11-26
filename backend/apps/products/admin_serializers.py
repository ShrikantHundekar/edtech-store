from rest_framework import serializers
from django.utils.text import slugify
from apps.catalog.models import Board, ClassLevel, Subject, Chapter
from .models import Product, Price, BundleItem


class AdminPriceSerializer(serializers.ModelSerializer):
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
            'created_at',
        )

    def get_amount_inr(self, obj):
        return obj.amount_paise / 100.0


class AdminBundleItemSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    class Meta:
        model = BundleItem
        fields = (
            'id',
            'target_type',
            'chapter',
            'subject',
            'title',
        )

    def get_title(self, obj):
        if obj.target_type == BundleItem.TARGET_TYPE_CHAPTER and obj.chapter:
            return obj.chapter.title
        elif obj.target_type == BundleItem.TARGET_TYPE_SUBJECT and obj.subject:
            return obj.subject.name
        return "Unknown"


class AdminProductSerializer(serializers.ModelSerializer):
    """
    Serializer for Admin CRUD operations on Products.
    Accepts price in paise (and optionally price_inr during write) and manages Price creation/updates.
    """
    slug = serializers.SlugField(required=False)
    product_type_display = serializers.CharField(source='get_product_type_display', read_only=True)
    board_name = serializers.CharField(source='board.name', read_only=True)
    class_name = serializers.CharField(source='academic_class.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    price_paise = serializers.IntegerField(source='current_price_paise', read_only=True)
    price_inr = serializers.FloatField(source='current_price_inr', read_only=True)
    current_price_paise = serializers.IntegerField(read_only=True)
    current_price_inr = serializers.FloatField(read_only=True)
    access_duration = serializers.CharField(read_only=True)
    pass_duration_days = serializers.IntegerField(read_only=True)
    inclusions = serializers.SerializerMethodField()

    # Write-only field for price creation/updates
    amount_paise = serializers.IntegerField(write_only=True, required=False)

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
            'current_price_paise',
            'current_price_inr',
            'amount_paise',
            'access_duration',
            'pass_duration_days',
            'inclusions',
            'created_at',
            'updated_at',
        )

    def get_inclusions(self, obj):
        return obj.get_inclusions()

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)

        # Generate slug if omitted
        if not data.get('slug') and data.get('title'):
            data['slug'] = slugify(data['title'])

        return super().to_internal_value(data)

    def validate(self, attrs):
        product_type = attrs.get('product_type') or (self.instance.product_type if self.instance else None)
        chapter = attrs.get('chapter') or (self.instance.chapter if self.instance else None)
        subject = attrs.get('subject') or (self.instance.subject if self.instance else None)
        academic_class = attrs.get('academic_class') or (self.instance.academic_class if self.instance else None)
        board = attrs.get('board') or (self.instance.board if self.instance else None)

        # Scope inference and consistency
        if product_type in (Product.PRODUCT_TYPE_CHAPTER_NOTES, Product.PRODUCT_TYPE_FREE_SAMPLE):
            if not chapter:
                raise serializers.ValidationError({"chapter": "Chapter is required for Chapter Notes and Free Sample products."})
            # Auto-infer subject, class, board from chapter
            attrs['subject'] = chapter.subject
            attrs['academic_class'] = chapter.subject.academic_class
            attrs['board'] = chapter.subject.academic_class.board

        elif product_type == Product.PRODUCT_TYPE_SUBJECT_PACK:
            if not subject:
                raise serializers.ValidationError({"subject": "Subject is required for Subject Pack products."})
            # Auto-infer class, board from subject
            attrs['academic_class'] = subject.academic_class
            attrs['board'] = subject.academic_class.board
            attrs['chapter'] = None

        elif product_type in (Product.PRODUCT_TYPE_MONTHLY_PASS, Product.PRODUCT_TYPE_ANNUAL_PASS):
            if not academic_class:
                raise serializers.ValidationError({"academic_class": "Class is required for Class Pass products."})
            attrs['board'] = academic_class.board
            attrs['subject'] = None
            attrs['chapter'] = None

        return attrs

    def create(self, validated_data):
        amount_paise = validated_data.pop('amount_paise', None)
        product = Product.objects.create(**validated_data)

        # Handle price creation
        if product.product_type == Product.PRODUCT_TYPE_FREE_SAMPLE:
            # Free samples strictly have 0 paise or no price
            pass
        elif amount_paise is not None:
            Price.objects.create(
                product=product,
                amount_paise=amount_paise,
                is_current=True,
            )
        return product

    def update(self, instance, validated_data):
        amount_paise = validated_data.pop('amount_paise', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update price if provided and not free sample
        if instance.product_type != Product.PRODUCT_TYPE_FREE_SAMPLE and amount_paise is not None:
            current_price = instance.prices.filter(is_current=True).first()
            if not current_price or current_price.amount_paise != amount_paise:
                # Mark previous prices as not current
                instance.prices.filter(is_current=True).update(is_current=False)
                # Create new active price
                Price.objects.create(
                    product=instance,
                    amount_paise=amount_paise,
                    is_current=True,
                )

        return instance

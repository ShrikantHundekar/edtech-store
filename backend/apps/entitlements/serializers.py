from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Entitlement, ManualAccessLog

User = get_user_model()


class EntitlementSerializer(serializers.ModelSerializer):
    student_email = serializers.EmailField(source='user.email', read_only=True)
    is_active = serializers.BooleanField(source='is_currently_active', read_only=True)

    class Meta:
        model = Entitlement
        fields = [
            'id',
            'user',
            'student_email',
            'product_type',
            'scope_id',
            'access_type',
            'valid_from',
            'valid_until',
            'status',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ManualAccessLogSerializer(serializers.ModelSerializer):
    admin_email = serializers.EmailField(source='admin.email', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)

    class Meta:
        model = ManualAccessLog
        fields = [
            'id',
            'admin',
            'admin_email',
            'student',
            'student_email',
            'action',
            'entitlement',
            'reason',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ManualGrantRequestSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(required=True)
    product_type = serializers.ChoiceField(choices=Entitlement.PRODUCT_TYPE_CHOICES, required=True)
    scope_id = serializers.IntegerField(required=True)
    access_type = serializers.ChoiceField(choices=Entitlement.ACCESS_TYPE_CHOICES, default='LIFETIME')
    valid_until = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'Reason field is strictly mandatory.',
            'blank': 'Reason field is strictly mandatory.'
        }
    )

    def validate_reason(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Reason field is strictly mandatory.")
        return value.strip()


class ManualRevokeRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'Reason field is strictly mandatory.',
            'blank': 'Reason field is strictly mandatory.'
        }
    )

    def validate_reason(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Reason field is strictly mandatory.")
        return value.strip()

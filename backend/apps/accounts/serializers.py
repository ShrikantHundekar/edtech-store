from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for returning public/authenticated user profile data.
    """
    is_admin = serializers.BooleanField(read_only=True)
    is_student = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'full_name',
            'phone_number',
            'role',
            'is_admin',
            'is_student',
            'created_at',
        )
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for student self-registration.
    Automatically assigns role = STUDENT.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Password must meet security complexity rules"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone_number', 'password', 'confirm_password')

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate(self, attrs):
        confirm_password = attrs.get('confirm_password')
        password = attrs.get('password')
        if confirm_password and password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        # Validate password using Django's configured AUTH_PASSWORD_VALIDATORS
        validate_password(password)
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            phone_number=validated_data.get('phone_number', '')
        )
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for authenticating users via email & password
    and issuing JWT tokens.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": "Invalid email or password."})

        if not user.check_password(password):
            raise serializers.ValidationError({"error": "Invalid email or password."})

        if not user.is_active:
            raise serializers.ValidationError({"error": "This account is inactive. Please contact support."})

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Add custom claims
        refresh['email'] = user.email
        refresh['role'] = user.role
        refresh['full_name'] = user.full_name

        return {
            'user': user,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }

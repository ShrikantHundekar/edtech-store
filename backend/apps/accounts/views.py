from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Public endpoint for registering a new student account.
    Returns the newly created user profile and initial JWT access + refresh tokens.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens immediately upon registration
        refresh = RefreshToken.for_user(user)
        refresh['email'] = user.email
        refresh['role'] = user.role
        refresh['full_name'] = user.full_name

        profile_data = UserProfileSerializer(user).data

        return Response(
            {
                'message': 'Registration successful.',
                'user': profile_data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            },
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Public endpoint to authenticate via email and password.
    Returns user profile and JWT access + refresh tokens.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED if "error" in serializer.errors else status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        user = validated_data['user']
        tokens = validated_data['tokens']
        profile = UserProfileSerializer(user).data

        return Response(
            {
                'message': 'Login successful.',
                'user': profile,
                'tokens': tokens,
            },
            status=status.HTTP_200_OK
        )

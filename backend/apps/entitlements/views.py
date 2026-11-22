import logging
from django.contrib.auth import get_user_model
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from apps.accounts.permissions import IsAdminRole
from .models import Entitlement, ManualAccessLog
from .serializers import (
    EntitlementSerializer,
    ManualAccessLogSerializer,
    ManualGrantRequestSerializer,
    ManualRevokeRequestSerializer,
)
from .services import manual_grant_entitlement, manual_revoke_entitlement

User = get_user_model()
logger = logging.getLogger(__name__)


class AdminManualGrantEntitlementView(APIView):
    """
    POST /api/v1/admin/entitlements/grant/
    Allows administrators to manually grant student access licenses for support purposes.
    Strictly requires non-empty reason and logs audit entry.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, *args, **kwargs):
        serializer = ManualGrantRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        student = User.objects.filter(id=data['student_id']).first()
        if not student:
            return Response(
                {"error": f"Student with ID {data['student_id']} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            entitlement, log_entry = manual_grant_entitlement(
                admin_user=request.user,
                student_user=student,
                product_type=data['product_type'],
                scope_id=data['scope_id'],
                reason=data['reason'],
                access_type=data.get('access_type', 'LIFETIME'),
                valid_until=data.get('valid_until')
            )
        except ValueError as e:
            return Response({"reason": [str(e)]}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Failed manual grant: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "message": "Entitlement granted successfully.",
                "entitlement": EntitlementSerializer(entitlement).data,
                "audit_log": ManualAccessLogSerializer(log_entry).data,
            },
            status=status.HTTP_201_CREATED
        )


class AdminManualRevokeEntitlementView(APIView):
    """
    POST /api/v1/admin/entitlements/{id}/revoke/
    Allows administrators to manually revoke student access licenses.
    Strictly requires non-empty reason and logs audit entry.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, pk, *args, **kwargs):
        serializer = ManualRevokeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        entitlement = Entitlement.objects.filter(id=pk).first()
        if not entitlement:
            return Response(
                {"error": f"Entitlement with ID {pk} does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            entitlement, log_entry = manual_revoke_entitlement(
                admin_user=request.user,
                entitlement_id=entitlement.id,
                reason=serializer.validated_data['reason']
            )
        except ValueError as e:
            return Response({"reason": [str(e)]}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Failed manual revoke: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "message": "Entitlement revoked successfully.",
                "entitlement": EntitlementSerializer(entitlement).data,
                "audit_log": ManualAccessLogSerializer(log_entry).data,
            },
            status=status.HTTP_200_OK
        )


class AdminManualAccessLogListView(ListAPIView):
    """
    GET /api/v1/admin/entitlements/logs/
    List of audit logs for manual access grants and revocations.
    """
    permission_classes = [IsAdminRole]
    serializer_class = ManualAccessLogSerializer
    queryset = ManualAccessLog.objects.select_related('admin', 'student', 'entitlement').all().order_by('-created_at')


class AdminEntitlementListView(ListAPIView):
    """
    GET /api/v1/admin/entitlements/
    Admin overview of all granted entitlements across students.
    """
    permission_classes = [IsAdminRole]
    serializer_class = EntitlementSerializer

    def get_queryset(self):
        qs = Entitlement.objects.select_related('user').all().order_by('-created_at')
        student_id = self.request.query_params.get('student_id')
        if student_id:
            qs = qs.filter(user_id=student_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

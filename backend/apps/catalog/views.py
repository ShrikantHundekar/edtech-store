from rest_framework import viewsets, permissions
from apps.accounts.permissions import IsAdminRole
from .models import Board, ClassLevel, Subject, Chapter, Material
from .serializers import BoardSerializer, ClassLevelSerializer


class AdminBoardViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD ViewSet for Educational Boards.
    Protected strictly with IsAdminRole. Non-admins receive HTTP 403.
    """
    queryset = Board.objects.all().order_by('name')
    serializer_class = BoardSerializer
    permission_classes = [IsAdminRole]


class AdminClassViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD ViewSet for Academic Classes linked to Boards.
    Protected strictly with IsAdminRole.
    """
    queryset = ClassLevel.objects.select_related('board').all().order_by('board', 'name')
    serializer_class = ClassLevelSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = super().get_queryset()
        board_id = self.request.query_params.get('board_id')
        if board_id:
            qs = qs.filter(board_id=board_id)
        return qs

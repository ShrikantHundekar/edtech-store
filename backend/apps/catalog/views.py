from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsAdminRole
from .models import Board, ClassLevel, Subject, Chapter, Material
from .serializers import (
    BoardSerializer,
    ClassLevelSerializer,
    SubjectSerializer,
    ChapterSerializer,
)


# =====================================================================
# ADMIN VIEWSETS (Protected via IsAdminRole, Non-Admin gets HTTP 403)
# =====================================================================

class AdminBoardViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD ViewSet for Educational Boards.
    """
    queryset = Board.objects.all().order_by('name')
    serializer_class = BoardSerializer
    permission_classes = [IsAdminRole]


class AdminClassViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD ViewSet for Academic Classes linked to Boards.
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


class AdminSubjectViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD ViewSet for Academic Subjects.
    """
    queryset = Subject.objects.select_related('academic_class__board').prefetch_related('chapters').all().order_by('academic_class', 'name')
    serializer_class = SubjectSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = super().get_queryset()
        class_id = self.request.query_params.get('class_id')
        if class_id:
            qs = qs.filter(academic_class_id=class_id)
        return qs


class AdminChapterViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD ViewSet for Chapters.
    """
    queryset = Chapter.objects.select_related('subject__academic_class__board').prefetch_related('materials').all().order_by('subject', 'chapter_number')
    serializer_class = ChapterSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = super().get_queryset()
        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        return qs


# =====================================================================
# PUBLIC HIERARCHICAL BROWSING VIEWS (AllowAny)
# =====================================================================

class PublicBoardListView(generics.ListAPIView):
    """
    GET /api/v1/catalog/boards/
    Returns list of all active education boards.
    """
    queryset = Board.objects.all().order_by('name')
    serializer_class = BoardSerializer
    permission_classes = [permissions.AllowAny]


class PublicBoardClassesListView(generics.ListAPIView):
    """
    GET /api/v1/catalog/boards/{id}/classes/
    Returns list of classes belonging to a specific board.
    Returns 404 if board does not exist.
    """
    serializer_class = ClassLevelSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        board_id = self.kwargs.get('board_id')
        board = get_object_or_404(Board, id=board_id)
        return board.classes.all().order_by('name')


class PublicClassSubjectsListView(generics.ListAPIView):
    """
    GET /api/v1/catalog/classes/{id}/subjects/
    Returns list of subjects belonging to a specific class.
    Returns 404 if class does not exist.
    """
    serializer_class = SubjectSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        class_id = self.kwargs.get('class_id')
        academic_class = get_object_or_404(ClassLevel, id=class_id)
        return academic_class.subjects.all().order_by('name')


class PublicSubjectChaptersListView(generics.ListAPIView):
    """
    GET /api/v1/catalog/subjects/{id}/chapters/
    Returns list of chapters under a specific subject, including free sample flags.
    Returns 404 if subject does not exist.
    """
    serializer_class = ChapterSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        subject_id = self.kwargs.get('subject_id')
        subject = get_object_or_404(Subject, id=subject_id)
        return subject.chapters.all().order_by('chapter_number')

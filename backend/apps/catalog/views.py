import os
import uuid
from django.conf import settings
from django.http import FileResponse
from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.accounts.permissions import IsAdminRole
from apps.entitlements.services import has_access_to_material
from .models import Board, ClassLevel, Subject, Chapter, Material
from .serializers import (
    BoardSerializer,
    ClassLevelSerializer,
    SubjectSerializer,
    ChapterSerializer,
    MaterialSerializer,
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

    @action(
        detail=True,
        methods=['post'],
        url_path='upload-material',
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsAdminRole],
    )
    def upload_material(self, request, pk=None):
        """
        POST /api/v1/admin/chapters/{id}/upload-material/
        Validates MIME type strictly as application/pdf, enforces max size (25MB),
        and stores the file with a non-guessable UUID on private storage.
        """
        chapter = self.get_object()
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file uploaded. Please provide a "file" in the multipart form data.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Enforce maximum file size (25MB)
        max_size_bytes = 25 * 1024 * 1024
        if file_obj.size > max_size_bytes:
            return Response(
                {'error': f'File size exceeds the 25MB limit. Uploaded size is {file_obj.size / (1024*1024):.2f}MB.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Validate MIME type strictly application/pdf
        content_type = getattr(file_obj, 'content_type', '')
        if content_type != 'application/pdf':
            return Response(
                {'error': 'Invalid MIME type. Only application/pdf files are permitted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify magic PDF bytes in file header (%PDF-)
        header = file_obj.read(5)
        file_obj.seek(0)
        if not header.startswith(b'%PDF'):
            return Response(
                {'error': 'Invalid or corrupted PDF file header.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Store on private disk with non-guessable UUID filename
        protected_root = getattr(settings, 'PROTECTED_MEDIA_ROOT', settings.BASE_DIR / 'protected_media')
        materials_dir = os.path.join(protected_root, 'materials')
        os.makedirs(materials_dir, exist_ok=True)

        uuid_filename = f"{uuid.uuid4().hex}.pdf"
        relative_path = os.path.join('materials', uuid_filename).replace('\\', '/')
        absolute_path = os.path.join(materials_dir, uuid_filename)

        with open(absolute_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        title = request.data.get('title')
        if not title or not title.strip():
            title = os.path.splitext(file_obj.name)[0] or f"{chapter.title} Notes"

        material = Material.objects.create(
            chapter=chapter,
            title=title.strip(),
            file_path=relative_path,
            file_size_bytes=file_obj.size,
            mime_type='application/pdf',
        )

        serializer = MaterialSerializer(material)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['post'],
        url_path='toggle-free-sample',
        permission_classes=[IsAdminRole],
    )
    def toggle_free_sample(self, request, pk=None):
        """
        POST /api/v1/admin/chapters/{id}/toggle-free-sample/
        Toggles or sets the is_free_sample flag.
        Optional JSON body: {"is_free_sample": true/false}
        Enforces max 1 free sample chapter per subject.
        """
        chapter = self.get_object()
        desired_state = request.data.get('is_free_sample')
        if desired_state is None:
            new_state = not chapter.is_free_sample
        else:
            new_state = bool(desired_state)

        if new_state:
            other_free = Chapter.objects.filter(
                subject=chapter.subject,
                is_free_sample=True
            ).exclude(pk=chapter.pk).first()

            if other_free:
                return Response(
                    {
                        'error': f'Subject already has a free sample chapter: "{other_free.title}" (Ch {other_free.chapter_number}). Only one chapter per subject can be marked as a free sample.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        chapter.is_free_sample = new_state
        chapter.save(update_fields=['is_free_sample', 'updated_at'])
        serializer = self.get_serializer(chapter)
        return Response(serializer.data, status=status.HTTP_200_OK)




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


class PublicChapterDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/catalog/chapters/{chapter_id}/
    Returns details for a chapter including is_free_sample flag.
    Returns 404 if chapter does not exist.
    """
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    lookup_url_kwarg = 'chapter_id'



class CatalogSearchView(APIView):
    """
    GET /api/v1/catalog/search/?q={query}
    Public endpoint searching subjects and chapters by keyword (case-insensitive).
    Returns structured results with full breadcrumb metadata (Board -> Class -> Subject).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response(
                {
                    "query": "",
                    "total_count": 0,
                    "subjects": [],
                    "chapters": []
                },
                status=status.HTTP_200_OK
            )

        # 1. Search Subjects
        subjects = Subject.objects.select_related(
            'academic_class__board'
        ).filter(
            Q(name__icontains=query)
        ).order_by('academic_class__board__name', 'academic_class__name', 'name')[:20]

        subject_results = [
            {
                "id": sub.id,
                "name": sub.name,
                "slug": sub.slug,
                "thumbnail_url": sub.thumbnail_url,
                "breadcrumbs": {
                    "board": {
                        "id": sub.academic_class.board.id,
                        "name": sub.academic_class.board.name,
                        "slug": sub.academic_class.board.slug,
                    },
                    "class": {
                        "id": sub.academic_class.id,
                        "name": sub.academic_class.name,
                        "slug": sub.academic_class.slug,
                    },
                },
                "breadcrumb_trail": f"{sub.academic_class.board.name} > {sub.academic_class.name}"
            }
            for sub in subjects
        ]

        # 2. Search Chapters
        chapters = Chapter.objects.select_related(
            'subject__academic_class__board'
        ).filter(
            Q(title__icontains=query)
        ).order_by('subject__academic_class__board__name', 'subject__name', 'chapter_number')[:30]

        chapter_results = [
            {
                "id": ch.id,
                "title": ch.title,
                "slug": ch.slug,
                "chapter_number": ch.chapter_number,
                "is_free_sample": ch.is_free_sample,
                "breadcrumbs": {
                    "board": {
                        "id": ch.subject.academic_class.board.id,
                        "name": ch.subject.academic_class.board.name,
                        "slug": ch.subject.academic_class.board.slug,
                    },
                    "class": {
                        "id": ch.subject.academic_class.id,
                        "name": ch.subject.academic_class.name,
                        "slug": ch.subject.academic_class.slug,
                    },
                    "subject": {
                        "id": ch.subject.id,
                        "name": ch.subject.name,
                        "slug": ch.subject.slug,
                    }
                },
                "breadcrumb_trail": f"{ch.subject.academic_class.board.name} > {ch.subject.academic_class.name} > {ch.subject.name}"
            }
            for ch in chapters
        ]

        return Response(
            {
                "query": query,
                "total_count": len(subject_results) + len(chapter_results),
                "subjects": subject_results,
                "chapters": chapter_results
            },
            status=status.HTTP_200_OK
        )


class MaterialDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/materials/{material_id}/
    Returns metadata for a study note.
    """
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    lookup_url_kwarg = 'material_id'


class MaterialStreamView(APIView):
    """
    GET /api/v1/materials/{material_id}/stream/
    Protected PDF streaming endpoint.
    Verifies user entitlement before serving the file:
    - If chapter is_free_sample: allows access without purchase.
    - If user is ADMIN: allows access.
    - If user has active Entitlement (Chapter, Subject Pack, or Class Pass): streams PDF.
    - If un-entitled: returns HTTP 403 Forbidden.
    - If file not found: returns HTTP 404 Not Found.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, material_id, *args, **kwargs):
        material = get_object_or_404(
            Material.objects.select_related('chapter__subject__academic_class'),
            id=material_id
        )

        # Entitlement authorization check
        if not has_access_to_material(request.user, material):
            return Response(
                {
                    "error": "Access denied. You do not hold an active entitlement for this study material. Please purchase the corresponding chapter, subject pack, or class pass."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Locate protected file on disk
        protected_root = getattr(settings, 'PROTECTED_MEDIA_ROOT', settings.BASE_DIR / 'protected_media')
        if os.path.isabs(material.file_path):
            file_path = material.file_path
        else:
            file_path = os.path.join(protected_root, material.file_path)

        if not os.path.exists(file_path):
            return Response(
                {"error": "Material file could not be found on the storage server."},
                status=status.HTTP_404_NOT_FOUND
            )

        file_handle = open(file_path, 'rb')
        response = FileResponse(file_handle, content_type='application/pdf')
        filename = f"{material.title}.pdf".replace('"', '')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


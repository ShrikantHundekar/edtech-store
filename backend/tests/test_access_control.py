import os
from datetime import timedelta
import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.catalog.models import Board, ClassLevel, Subject, Chapter, Material
from apps.entitlements.models import Entitlement
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestAccessControlAndSecurity:
    """
    Issue #53: Access control tests for locked PDFs and admin endpoints.
    Test Scenarios:
    - Un-entitled user requesting /materials/{id}/stream/ receives HTTP 403 Forbidden.
    - Student calling /api/v1/admin/* receives HTTP 403 Forbidden.
    - Expired pass holder receives HTTP 403.
    """

    @pytest.fixture(autouse=True)
    def setup_entities(self, tmp_path):
        self.student = User.objects.create_user(
            email="student_acl@example.com",
            password="StudentPassword123!",
            role="STUDENT"
        )
        self.admin = User.objects.create_user(
            email="admin_acl@example.com",
            password="AdminPassword123!",
            role="ADMIN"
        )

        self.board = Board.objects.create(name="CBSE ACL", slug="cbse-acl")
        self.cls = ClassLevel.objects.create(board=self.board, name="Class 10", slug="c10-acl")
        self.subject = Subject.objects.create(academic_class=self.cls, name="Geography", slug="geo-acl")
        self.chapter = Chapter.objects.create(
            subject=self.subject,
            chapter_number=1,
            title="Resources and Development",
            slug="resources-dev",
            is_free_sample=False  # Locked chapter
        )

        # Create temporary material file
        protected_root = getattr(settings, 'PROTECTED_MEDIA_ROOT', settings.BASE_DIR / 'protected_media')
        mat_dir = os.path.join(protected_root, 'materials')
        os.makedirs(mat_dir, exist_ok=True)
        pdf_path = os.path.join(mat_dir, 'locked_note_acl_test.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(b"%PDF-1.4 Mock Encrypted Secure Study Material Content")

        self.material = Material.objects.create(
            chapter=self.chapter,
            title="Class 10 Geography Notes",
            file_path="materials/locked_note_acl_test.pdf",
            file_size_bytes=52,
            mime_type="application/pdf"
        )

        yield

        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError:
                pass

    def test_unentitled_user_streaming_material_receives_403(self):
        """Un-entitled user requesting locked material receives HTTP 403 Forbidden."""
        client = APIClient()
        client.force_authenticate(user=self.student)

        response = client.get(f'/api/v1/materials/{self.material.id}/stream/')
        assert response.status_code == 403
        assert "Access denied" in str(response.data)

    def test_expired_pass_holder_streaming_material_receives_403(self):
        """Expired class pass holder receives HTTP 403 Forbidden."""
        now = timezone.now()
        # Expired class pass (expired 5 days ago)
        Entitlement.objects.create(
            user=self.student,
            product_type='CLASS_PASS',
            scope_id=self.cls.id,
            access_type='TIME_BOUND',
            valid_from=now - timedelta(days=35),
            valid_until=now - timedelta(days=5),
            status='ACTIVE'
        )

        client = APIClient()
        client.force_authenticate(user=self.student)

        response = client.get(f'/api/v1/materials/{self.material.id}/stream/')
        assert response.status_code == 403
        assert "Access denied" in str(response.data)

    def test_student_calling_admin_endpoints_receives_403(self):
        """Student calling admin endpoints (/api/v1/admin/*) receives HTTP 403 Forbidden."""
        client = APIClient()
        client.force_authenticate(user=self.student)

        # Admin boards endpoint
        resp_boards = client.get('/api/v1/admin/boards/')
        assert resp_boards.status_code == 403

        # Admin classes endpoint
        resp_classes = client.get('/api/v1/admin/classes/')
        assert resp_classes.status_code == 403

        # Admin subjects endpoint
        resp_subj = client.get('/api/v1/admin/subjects/')
        assert resp_subj.status_code == 403

        # Admin entitlements grant endpoint
        resp_grant = client.post('/api/v1/admin/entitlements/grant/', {}, format='json')
        assert resp_grant.status_code == 403

    def test_entitled_student_and_admin_receive_200(self):
        """Entitled student or admin receives HTTP 200 with streamed file."""
        # Active lifetime entitlement granted
        Entitlement.objects.create(
            user=self.student,
            product_type='CHAPTER',
            scope_id=self.chapter.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        client = APIClient()
        client.force_authenticate(user=self.student)
        resp_student = client.get(f'/api/v1/materials/{self.material.id}/stream/')
        assert resp_student.status_code == 200

        # Admin bypass
        client.force_authenticate(user=self.admin)
        resp_admin = client.get(f'/api/v1/materials/{self.material.id}/stream/')
        assert resp_admin.status_code == 200

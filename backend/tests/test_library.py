import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.catalog.models import Board, ClassLevel, Subject, Chapter, Material
from apps.entitlements.models import Entitlement

User = get_user_model()

@pytest.mark.django_db
class TestStudentLibraryAndReader:
    @pytest.fixture
    def setup_data(self):
        board = Board.objects.create(name="CBSE Library", slug="cbse-lib")
        class_10 = ClassLevel.objects.create(name="Class 10 Lib", slug="class-10-lib", board=board)
        subject = Subject.objects.create(name="Science Lib", slug="science-lib", academic_class=class_10)
        chapter = Chapter.objects.create(title="Chemical Reactions Lib", subject=subject, chapter_number=1)
        material = Material.objects.create(
            chapter=chapter,
            title="Formula Sheet Lib",
            file_path="materials/sample.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024
        )

        student = User.objects.create_user(
            email="student_library@test.com",
            password="StrongPassword123!",
            role="STUDENT"
        )

        return {
            "board": board,
            "class_10": class_10,
            "subject": subject,
            "chapter": chapter,
            "material": material,
            "student": student,
        }

    def test_unauthenticated_library_access_returns_401(self):
        client = APIClient()
        response = client.get("/api/v1/entitlements/my-library/")
        assert response.status_code == 401

    def test_student_library_reflects_active_passes_and_chapters(self, setup_data):
        client = APIClient()
        client.force_authenticate(user=setup_data["student"])

        # Create active 30-day class pass
        now = timezone.now()
        Entitlement.objects.create(
            user=setup_data["student"],
            product_type="CLASS_PASS",
            scope_id=setup_data["class_10"].id,
            access_type="TIME_BOUND",
            valid_from=now,
            valid_until=now + timedelta(days=20),
            status="ACTIVE"
        )

        response = client.get("/api/v1/entitlements/my-library/")
        assert response.status_code == 200
        data = response.data

        # Check passes list and countdown
        assert len(data["passes"]) == 1
        pass_entry = data["passes"][0]
        assert pass_entry["class_id"] == setup_data["class_10"].id
        assert pass_entry["is_active"] is True
        assert pass_entry["remaining_days"] in (20, 21)
        assert "days left" in pass_entry["countdown_text"]

        # Check unlocked chapter via class pass
        assert len(data["chapters"]) >= 1
        ch_entry = next((c for c in data["chapters"] if c["id"] == setup_data["chapter"].id), None)
        assert ch_entry is not None
        assert ch_entry["unlocked_via"] == "CLASS_PASS"
        assert len(ch_entry["materials"]) == 1
        assert ch_entry["materials"][0]["stream_url"] == f"/api/v1/materials/{setup_data['material'].id}/stream/"

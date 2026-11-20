import os
import shutil
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.entitlements.models import Entitlement
from .models import Board, ClassLevel, Subject, Chapter, Material

User = get_user_model()


class CatalogModelTests(TestCase):
    def setUp(self):
        self.board = Board.objects.create(
            name="CBSE",
            slug="cbse",
            description="Central Board of Secondary Education"
        )
        self.academic_class = ClassLevel.objects.create(
            board=self.board,
            name="Class 10",
            slug="class-10"
        )
        self.subject = Subject.objects.create(
            academic_class=self.academic_class,
            name="Mathematics",
            slug="mathematics"
        )
        self.chapter = Chapter.objects.create(
            subject=self.subject,
            chapter_number=1,
            title="Real Numbers",
            slug="real-numbers",
            is_free_sample=True
        )
        self.material = Material.objects.create(
            chapter=self.chapter,
            title="Real Numbers Revision Notes",
            file_path="protected_media/notes/cbse_10_math_ch1.pdf",
            file_size_bytes=1048576,
            mime_type="application/pdf"
        )

    def test_model_creation_and_string_representations(self):
        self.assertEqual(str(self.board), "CBSE")
        self.assertEqual(str(self.academic_class), "CBSE - Class 10")
        self.assertEqual(str(self.subject), "CBSE - Class 10 - Mathematics")
        self.assertEqual(str(self.chapter), "Mathematics - Ch 1: Real Numbers")
        self.assertEqual(str(self.material), "Real Numbers - Real Numbers Revision Notes")

    def test_material_attributes_and_relationships(self):
        self.assertEqual(self.material.chapter, self.chapter)
        self.assertEqual(self.material.mime_type, "application/pdf")
        self.assertEqual(self.material.file_size_bytes, 1048576)
        self.assertIn("protected_media", self.material.file_path)

    def test_unique_constraints(self):
        # Duplicate board slug should raise error
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Board.objects.create(name="CBSE Copy", slug="cbse")

        # Duplicate chapter number within same subject should raise error
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Chapter.objects.create(
                    subject=self.subject,
                    chapter_number=1,
                    title="Duplicate Chapter",
                    slug="duplicate-chapter"
                )

    def test_cascade_deletion(self):
        # Deleting a board should cascade delete classes, subjects, and chapters
        board_id = self.board.id
        self.board.delete()
        self.assertFalse(ClassLevel.objects.filter(board_id=board_id).exists())
        self.assertFalse(Subject.objects.filter(academic_class__board_id=board_id).exists())
        self.assertFalse(Chapter.objects.filter(subject__academic_class__board_id=board_id).exists())


class AdminCatalogAPITests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="curriculumadmin@example.com",
            password="AdminPassword123!",
            full_name="Curriculum Admin"
        )
        self.student_user = User.objects.create_user(
            email="regularstudent@example.com",
            password="StudentPassword123!",
            full_name="Regular Student"
        )
        self.board = Board.objects.create(
            name="CBSE",
            slug="cbse",
            description="Central Board"
        )
        self.academic_class = ClassLevel.objects.create(
            board=self.board,
            name="Class 10",
            slug="class-10"
        )
        self.subject = Subject.objects.create(
            academic_class=self.academic_class,
            name="Mathematics",
            slug="mathematics"
        )
        self.chapter = Chapter.objects.create(
            subject=self.subject,
            chapter_number=1,
            title="Real Numbers",
            slug="real-numbers",
            is_free_sample=True
        )

        admin_refresh = RefreshToken.for_user(self.admin_user)
        self.admin_token = str(admin_refresh.access_token)

        student_refresh = RefreshToken.for_user(self.student_user)
        self.student_token = str(student_refresh.access_token)

    def test_admin_can_list_and_create_boards(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # 1. List boards
        list_resp = self.client.get('/api/v1/admin/boards/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_resp.data), 1)

        # 2. Create new board
        create_resp = self.client.post('/api/v1/admin/boards/', {
            "name": "ICSE",
            "description": "Indian Certificate of Secondary Education"
        }, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data['name'], "ICSE")
        self.assertEqual(create_resp.data['slug'], "icse")

    def test_admin_can_update_and_delete_board(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        patch_resp = self.client.patch(f'/api/v1/admin/boards/{self.board.id}/', {
            "description": "Updated CBSE Description"
        }, format='json')
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data['description'], "Updated CBSE Description")

        delete_resp = self.client.delete(f'/api/v1/admin/boards/{self.board.id}/')
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Board.objects.filter(id=self.board.id).exists())

    def test_admin_can_create_and_filter_classes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        create_resp = self.client.post('/api/v1/admin/classes/', {
            "board": self.board.id,
            "name": "Class 12"
        }, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data['name'], "Class 12")
        self.assertEqual(create_resp.data['slug'], "class-12")

        list_resp = self.client.get(f'/api/v1/admin/classes/?board_id={self.board.id}')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 2)

    def test_admin_crud_subjects(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Create subject
        create_resp = self.client.post('/api/v1/admin/subjects/', {
            "academic_class": self.academic_class.id,
            "name": "Science",
            "thumbnail_url": "https://example.com/science.png"
        }, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data['name'], "Science")
        self.assertEqual(create_resp.data['slug'], "science")

        # List subjects filtered by class
        list_resp = self.client.get(f'/api/v1/admin/subjects/?class_id={self.academic_class.id}')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 2)

    def test_admin_crud_chapters(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Create chapter
        create_resp = self.client.post('/api/v1/admin/chapters/', {
            "subject": self.subject.id,
            "chapter_number": 2,
            "title": "Polynomials",
            "is_free_sample": False
        }, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data['chapter_number'], 2)
        self.assertEqual(create_resp.data['slug'], "polynomials")

        # Duplicate chapter number in same subject fails
        dup_resp = self.client.post('/api/v1/admin/chapters/', {
            "subject": self.subject.id,
            "chapter_number": 2,
            "title": "Another Chapter 2"
        }, format='json')
        self.assertEqual(dup_resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_forbidden_from_admin_catalog(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        
        self.assertEqual(self.client.get('/api/v1/admin/boards/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get('/api/v1/admin/classes/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get('/api/v1/admin/subjects/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get('/api/v1/admin/chapters/').status_code, status.HTTP_403_FORBIDDEN)


class PublicCatalogAPITests(APITestCase):
    def setUp(self):
        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Mathematics", slug="math")
        self.chapter1 = Chapter.objects.create(
            subject=self.subject,
            chapter_number=1,
            title="Real Numbers",
            slug="real-numbers",
            is_free_sample=True
        )
        self.chapter2 = Chapter.objects.create(
            subject=self.subject,
            chapter_number=2,
            title="Polynomials",
            slug="polynomials",
            is_free_sample=False
        )

    def test_public_browsing_boards(self):
        # Public request without any Authorization header
        response = self.client.get('/api/v1/catalog/boards/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "CBSE")

    def test_public_browsing_board_classes(self):
        # Classes for existing board
        response = self.client.get(f'/api/v1/catalog/boards/{self.board.id}/classes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Class 10")

        # 404 for non-existent board
        resp_404 = self.client.get('/api/v1/catalog/boards/99999/classes/')
        self.assertEqual(resp_404.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_browsing_class_subjects(self):
        # Subjects for existing class
        response = self.client.get(f'/api/v1/catalog/classes/{self.academic_class.id}/subjects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Mathematics")

        # 404 for non-existent class
        resp_404 = self.client.get('/api/v1/catalog/classes/99999/subjects/')
        self.assertEqual(resp_404.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_browsing_subject_chapters(self):
        # Chapters for existing subject (showing is_free_sample flags)
        response = self.client.get(f'/api/v1/catalog/subjects/{self.subject.id}/chapters/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Chapter 1 is free sample
        self.assertTrue(response.data[0]['is_free_sample'])
        self.assertEqual(response.data[0]['title'], "Real Numbers")

        # Chapter 2 is locked
        self.assertFalse(response.data[1]['is_free_sample'])
        self.assertEqual(response.data[1]['title'], "Polynomials")

        # 404 for non-existent subject
        resp_404 = self.client.get('/api/v1/catalog/subjects/99999/chapters/')
        self.assertEqual(resp_404.status_code, status.HTTP_404_NOT_FOUND)

    def test_search_by_chapter_title_returns_breadcrumbs(self):
        # Search for 'Real' (matches Chapter: Real Numbers)
        response = self.client.get('/api/v1/catalog/search/?q=Real')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['total_count'], 1)
        self.assertEqual(len(response.data['chapters']), 1)
        
        chapter_res = response.data['chapters'][0]
        self.assertEqual(chapter_res['title'], "Real Numbers")
        self.assertEqual(chapter_res['breadcrumbs']['board']['name'], "CBSE")
        self.assertEqual(chapter_res['breadcrumbs']['class']['name'], "Class 10")
        self.assertEqual(chapter_res['breadcrumbs']['subject']['name'], "Mathematics")
        self.assertEqual(chapter_res['breadcrumb_trail'], "CBSE > Class 10 > Mathematics")

    def test_search_by_subject_name_returns_breadcrumbs(self):
        # Search for 'Math' (matches Subject: Mathematics)
        response = self.client.get('/api/v1/catalog/search/?q=math')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['total_count'], 1)
        self.assertEqual(len(response.data['subjects']), 1)
        
        subject_res = response.data['subjects'][0]
        self.assertEqual(subject_res['name'], "Mathematics")
        self.assertEqual(subject_res['breadcrumbs']['board']['name'], "CBSE")
        self.assertEqual(subject_res['breadcrumbs']['class']['name'], "Class 10")
        self.assertEqual(subject_res['breadcrumb_trail'], "CBSE > Class 10")

    def test_search_case_insensitive(self):
        resp_upper = self.client.get('/api/v1/catalog/search/?q=POLYNOMIALS')
        resp_lower = self.client.get('/api/v1/catalog/search/?q=polynomials')
        self.assertEqual(resp_upper.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_lower.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_upper.data['chapters']), 1)
        self.assertEqual(len(resp_lower.data['chapters']), 1)
        self.assertEqual(resp_upper.data['chapters'][0]['title'], resp_lower.data['chapters'][0]['title'])

    def test_search_empty_and_no_match(self):
        # Empty query
        resp_empty = self.client.get('/api/v1/catalog/search/')
        self.assertEqual(resp_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_empty.data['total_count'], 0)
        self.assertEqual(len(resp_empty.data['subjects']), 0)
        self.assertEqual(len(resp_empty.data['chapters']), 0)

        # No match query
        resp_no_match = self.client.get('/api/v1/catalog/search/?q=QuantumMechanics404')
        self.assertEqual(resp_no_match.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_no_match.data['total_count'], 0)


class AdminMaterialUploadTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin_uploader@test.com",
            password="AdminPassword123!",
            role="ADMIN"
        )
        self.student_user = User.objects.create_user(
            email="student_uploader@test.com",
            password="StudentPassword123!",
            role="STUDENT"
        )
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.student_token = str(RefreshToken.for_user(self.student_user).access_token)

        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Physics", slug="physics")
        self.chapter = Chapter.objects.create(
            subject=self.subject,
            chapter_number=1,
            title="Light - Reflection and Refraction",
            slug="light-reflection"
        )

        self.created_files = []

    def tearDown(self):
        # Clean up files created during tests
        protected_root = getattr(settings, 'PROTECTED_MEDIA_ROOT', settings.BASE_DIR / 'protected_media')
        for rel_path in self.created_files:
            full_path = os.path.join(protected_root, rel_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError:
                    pass

    def test_admin_successful_pdf_upload(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        pdf_content = b"%PDF-1.4 sample binary pdf stream data with valid header"
        pdf_file = SimpleUploadedFile("formula_sheet.pdf", pdf_content, content_type="application/pdf")

        url = f'/api/v1/admin/chapters/{self.chapter.id}/upload-material/'
        response = self.client.post(url, {
            'file': pdf_file,
            'title': 'Formula Sheet & Diagrams'
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data['title'], 'Formula Sheet & Diagrams')
        self.assertEqual(data['mime_type'], 'application/pdf')
        self.assertEqual(data['chapter'], self.chapter.id)
        self.assertEqual(data['file_size_bytes'], len(pdf_content))
        self.assertTrue(data['file_path'].endswith('.pdf'))
        self.assertTrue(data['file_path'].startswith('materials/'))

        self.created_files.append(data['file_path'])

        # Verify file is stored on private disk with non-guessable UUID
        protected_root = getattr(settings, 'PROTECTED_MEDIA_ROOT', settings.BASE_DIR / 'protected_media')
        full_path = os.path.join(protected_root, data['file_path'])
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, 'rb') as f:
            self.assertEqual(f.read(), pdf_content)

        # Verify database record
        material = Material.objects.get(id=data['id'])
        self.assertEqual(material.chapter, self.chapter)
        self.assertEqual(material.title, 'Formula Sheet & Diagrams')
        self.assertEqual(material.file_path, data['file_path'])

    def test_admin_upload_rejects_non_pdf_mime_type(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        text_file = SimpleUploadedFile("notes.txt", b"Plain text note content", content_type="text/plain")

        url = f'/api/v1/admin/chapters/{self.chapter.id}/upload-material/'
        response = self.client.post(url, {'file': text_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("application/pdf", response.data['error'])

    def test_admin_upload_rejects_corrupt_header_pdf(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        # MIME type claims to be PDF, but header is not %PDF
        fake_pdf = SimpleUploadedFile("fake.pdf", b"NOTAPDF header content", content_type="application/pdf")

        url = f'/api/v1/admin/chapters/{self.chapter.id}/upload-material/'
        response = self.client.post(url, {'file': fake_pdf}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or corrupted PDF file header", response.data['error'])

    def test_admin_upload_rejects_oversized_file(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        # 25MB + 1KB
        oversized_data = b"%PDF-" + b"0" * (25 * 1024 * 1024 + 1024)
        big_file = SimpleUploadedFile("big.pdf", oversized_data, content_type="application/pdf")

        url = f'/api/v1/admin/chapters/{self.chapter.id}/upload-material/'
        response = self.client.post(url, {'file': big_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("File size exceeds the 25MB limit", response.data['error'])

    def test_admin_upload_missing_file_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        url = f'/api/v1/admin/chapters/{self.chapter.id}/upload-material/'
        response = self.client.post(url, {'title': 'Empty'}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_forbidden_from_upload(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        pdf_file = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 doc", content_type="application/pdf")

        url = f'/api/v1/admin/chapters/{self.chapter.id}/upload-material/'
        response = self.client.post(url, {'file': pdf_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_upload(self):
        pdf_file = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 doc", content_type="application/pdf")
        url = f'/api/v1/admin/chapters/{self.chapter.id}/upload-material/'
        response = self.client.post(url, {'file': pdf_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FreeSampleChapterTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin_free_sample@test.com",
            password="AdminPassword123!",
            role="ADMIN"
        )
        self.student_user = User.objects.create_user(
            email="student_free_sample@test.com",
            password="StudentPassword123!",
            role="STUDENT"
        )
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.student_token = str(RefreshToken.for_user(self.student_user).access_token)

        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.subject = Subject.objects.create(academic_class=self.academic_class, name="Biology", slug="biology")
        self.chapter1 = Chapter.objects.create(
            subject=self.subject,
            chapter_number=1,
            title="Life Processes",
            slug="life-processes",
            is_free_sample=True
        )
        self.chapter2 = Chapter.objects.create(
            subject=self.subject,
            chapter_number=2,
            title="Control and Coordination",
            slug="control-and-coordination",
            is_free_sample=False
        )

    def test_model_level_enforces_single_free_sample_per_subject(self):
        with self.assertRaises(ValidationError):
            Chapter.objects.create(
                subject=self.subject,
                chapter_number=3,
                title="How do Organisms Reproduce?",
                slug="reproduction",
                is_free_sample=True
            )

    def test_admin_create_rejects_second_free_sample_in_same_subject(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post('/api/v1/admin/chapters/', {
            "subject": self.subject.id,
            "chapter_number": 3,
            "title": "Heredity and Evolution",
            "is_free_sample": True
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only one chapter per subject can be marked as a free sample", str(response.data))

    def test_admin_patch_rejects_second_free_sample_in_same_subject(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.patch(f'/api/v1/admin/chapters/{self.chapter2.id}/', {
            "is_free_sample": True
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only one chapter per subject can be marked as a free sample", str(response.data))

    def test_admin_can_reassign_free_sample_after_unsetting_previous(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # 1. Unset chapter 1
        resp1 = self.client.patch(f'/api/v1/admin/chapters/{self.chapter1.id}/', {
            "is_free_sample": False
        }, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertFalse(resp1.data['is_free_sample'])

        # 2. Set chapter 2 to free sample
        resp2 = self.client.patch(f'/api/v1/admin/chapters/{self.chapter2.id}/', {
            "is_free_sample": True
        }, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertTrue(resp2.data['is_free_sample'])

    def test_toggle_free_sample_action(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        # Chapter 1 is currently free; toggle it to false
        resp = self.client.post(f'/api/v1/admin/chapters/{self.chapter1.id}/toggle-free-sample/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['is_free_sample'])

        # Now chapter 2 can be toggled to true
        resp2 = self.client.post(f'/api/v1/admin/chapters/{self.chapter2.id}/toggle-free-sample/')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertTrue(resp2.data['is_free_sample'])

        # Toggling chapter 1 back to true while chapter 2 is free should return 400
        resp3 = self.client.post(f'/api/v1/admin/chapters/{self.chapter1.id}/toggle-free-sample/')
        self.assertEqual(resp3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only one chapter per subject can be marked as a free sample", resp3.data['error'])

    def test_public_catalog_endpoints_return_free_sample_flag(self):
        # 1. Subject chapters list endpoint
        resp_list = self.client.get(f'/api/v1/catalog/subjects/{self.subject.id}/chapters/')
        self.assertEqual(resp_list.status_code, status.HTTP_200_OK)
        chapters = {c['id']: c for c in resp_list.data}
        self.assertTrue(chapters[self.chapter1.id]['is_free_sample'])
        self.assertFalse(chapters[self.chapter2.id]['is_free_sample'])

        # 2. Chapter detail endpoint
        resp_detail = self.client.get(f'/api/v1/catalog/chapters/{self.chapter1.id}/')
        self.assertEqual(resp_detail.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_detail.data['is_free_sample'])
        self.assertEqual(resp_detail.data['title'], "Life Processes")

        # 3. Catalog search endpoint
        resp_search = self.client.get('/api/v1/catalog/search/?q=Processes')
        self.assertEqual(resp_search.status_code, status.HTTP_200_OK)
        found = next((ch for ch in resp_search.data['chapters'] if ch['id'] == self.chapter1.id), None)
        self.assertIsNotNone(found)
        self.assertTrue(found['is_free_sample'])


class ProtectedPDFStreamingTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin_stream@test.com",
            password="AdminPassword123!",
            role="ADMIN"
        )
        self.student_unentitled = User.objects.create_user(
            email="unentitled@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.student_chapter = User.objects.create_user(
            email="chapter_holder@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.student_subject = User.objects.create_user(
            email="subject_holder@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.student_class = User.objects.create_user(
            email="class_holder@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.student_expired = User.objects.create_user(
            email="expired_holder@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.student_revoked = User.objects.create_user(
            email="revoked_holder@test.com",
            password="Password123!",
            role="STUDENT"
        )
        self.student_other = User.objects.create_user(
            email="other_subject_holder@test.com",
            password="Password123!",
            role="STUDENT"
        )

        self.admin_token = str(RefreshToken.for_user(self.admin).access_token)
        self.unentitled_token = str(RefreshToken.for_user(self.student_unentitled).access_token)
        self.chapter_token = str(RefreshToken.for_user(self.student_chapter).access_token)
        self.subject_token = str(RefreshToken.for_user(self.student_subject).access_token)
        self.class_token = str(RefreshToken.for_user(self.student_class).access_token)
        self.expired_token = str(RefreshToken.for_user(self.student_expired).access_token)
        self.revoked_token = str(RefreshToken.for_user(self.student_revoked).access_token)
        self.other_token = str(RefreshToken.for_user(self.student_other).access_token)

        self.board = Board.objects.create(name="CBSE", slug="cbse")
        self.academic_class = ClassLevel.objects.create(board=self.board, name="Class 10", slug="class-10")
        self.science = Subject.objects.create(academic_class=self.academic_class, name="Science", slug="science")
        self.math = Subject.objects.create(academic_class=self.academic_class, name="Math", slug="math")

        # Chapter 1 is free sample
        self.ch_free = Chapter.objects.create(
            subject=self.science,
            chapter_number=1,
            title="Chemical Reactions",
            slug="chemical-reactions",
            is_free_sample=True
        )
        # Chapter 2 is locked paid chapter
        self.ch_paid = Chapter.objects.create(
            subject=self.science,
            chapter_number=2,
            title="Acids, Bases and Salts",
            slug="acids-bases",
            is_free_sample=False
        )

        # Write real test PDF files in PROTECTED_MEDIA_ROOT
        protected_root = getattr(settings, 'PROTECTED_MEDIA_ROOT', settings.BASE_DIR / 'protected_media')
        mat_dir = os.path.join(protected_root, 'materials')
        os.makedirs(mat_dir, exist_ok=True)

        self.free_pdf_rel = 'materials/test_free_note.pdf'
        self.paid_pdf_rel = 'materials/test_paid_note.pdf'
        self.free_pdf_full = os.path.join(protected_root, self.free_pdf_rel)
        self.paid_pdf_full = os.path.join(protected_root, self.paid_pdf_rel)

        self.free_content = b"%PDF-1.4 Free sample study notes content"
        self.paid_content = b"%PDF-1.4 Paid premium study notes content"

        with open(self.free_pdf_full, 'wb') as f:
            f.write(self.free_content)
        with open(self.paid_pdf_full, 'wb') as f:
            f.write(self.paid_content)

        self.free_material = Material.objects.create(
            chapter=self.ch_free,
            title="Free Chemical Reactions Summary",
            file_path=self.free_pdf_rel,
            file_size_bytes=len(self.free_content),
            mime_type='application/pdf'
        )
        self.paid_material = Material.objects.create(
            chapter=self.ch_paid,
            title="Acids and Bases Complete Guide",
            file_path=self.paid_pdf_rel,
            file_size_bytes=len(self.paid_content),
            mime_type='application/pdf'
        )

        # Create entitlements
        # 1. Chapter entitlement
        Entitlement.objects.create(
            user=self.student_chapter,
            product_type='CHAPTER',
            scope_id=self.ch_paid.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        # 2. Subject entitlement
        Entitlement.objects.create(
            user=self.student_subject,
            product_type='SUBJECT',
            scope_id=self.science.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

        # 3. Class pass entitlement (valid for 30 days)
        Entitlement.objects.create(
            user=self.student_class,
            product_type='CLASS_PASS',
            scope_id=self.academic_class.id,
            access_type='TIME_BOUND',
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=29),
            status='ACTIVE'
        )

        # 4. Expired class pass (expired 2 days ago)
        Entitlement.objects.create(
            user=self.student_expired,
            product_type='CLASS_PASS',
            scope_id=self.academic_class.id,
            access_type='TIME_BOUND',
            valid_from=timezone.now() - timedelta(days=32),
            valid_until=timezone.now() - timedelta(days=2),
            status='ACTIVE'
        )

        # 5. Revoked chapter entitlement
        Entitlement.objects.create(
            user=self.student_revoked,
            product_type='CHAPTER',
            scope_id=self.ch_paid.id,
            access_type='LIFETIME',
            status='REVOKED'
        )

        # 6. Entitlement for different subject (Math instead of Science)
        Entitlement.objects.create(
            user=self.student_other,
            product_type='SUBJECT',
            scope_id=self.math.id,
            access_type='LIFETIME',
            status='ACTIVE'
        )

    def tearDown(self):
        if os.path.exists(self.free_pdf_full):
            try:
                os.remove(self.free_pdf_full)
            except OSError:
                pass
        if os.path.exists(self.paid_pdf_full):
            try:
                os.remove(self.paid_pdf_full)
            except OSError:
                pass

    def test_free_sample_streamable_by_anonymous(self):
        # Anyone can stream free sample
        resp = self.client.get(f'/api/v1/materials/{self.free_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        content = b"".join(resp.streaming_content) if resp.streaming else resp.content
        self.assertEqual(content, self.free_content)

    def test_free_sample_streamable_by_authenticated_student(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.unentitled_token}')
        resp = self.client.get(f'/api/v1/materials/{self.free_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_paid_material_rejected_for_anonymous(self):
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_paid_material_rejected_for_unentitled_student(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.unentitled_token}')
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("do not hold an active entitlement", resp.data['error'])

    def test_paid_material_allowed_for_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        content = b"".join(resp.streaming_content) if resp.streaming else resp.content
        self.assertEqual(content, self.paid_content)

    def test_paid_material_allowed_with_chapter_entitlement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.chapter_token}')
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        content = b"".join(resp.streaming_content) if resp.streaming else resp.content
        self.assertEqual(content, self.paid_content)

    def test_paid_material_allowed_with_subject_pack(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.subject_token}')
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_paid_material_allowed_with_class_pass(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.class_token}')
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_paid_material_rejected_for_expired_pass(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.expired_token}')
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_paid_material_rejected_for_revoked_entitlement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.revoked_token}')
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_paid_material_rejected_for_different_subject_entitlement(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.other_token}')
        resp = self.client.get(f'/api/v1/materials/{self.paid_material.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_material_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        resp = self.client.get('/api/v1/materials/99999/stream/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_file_on_disk_returns_404(self):
        # Create DB record pointing to non-existent file
        ghost_mat = Material.objects.create(
            chapter=self.ch_free,
            title="Ghost Note",
            file_path="materials/non_existent_ghost.pdf",
            file_size_bytes=100,
            mime_type='application/pdf'
        )
        resp = self.client.get(f'/api/v1/materials/{ghost_mat.id}/stream/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("could not be found on the storage server", resp.data['error'])

    def test_direct_static_url_access_to_notes_is_forbidden(self):
        # Directly requesting /media/notes/... returns HTTP 403 Forbidden
        resp_notes = self.client.get('/media/notes/chapter1.pdf')
        self.assertEqual(resp_notes.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Direct static URL access to study notes is disallowed", resp_notes.json()['error'])

        # Directly requesting /media/materials/... returns HTTP 403 Forbidden
        resp_mats = self.client.get('/media/materials/chemical_reactions.pdf')
        self.assertEqual(resp_mats.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Direct static URL access to study notes is disallowed", resp_mats.json()['error'])

        # Directly requesting /protected_media/... returns HTTP 403 Forbidden
        resp_protected = self.client.get('/protected_media/materials/uuid.pdf')
        self.assertEqual(resp_protected.status_code, status.HTTP_403_FORBIDDEN)






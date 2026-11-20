from django.test import TestCase
from django.db import transaction
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
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


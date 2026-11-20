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


class AdminBoardAndClassAPITests(APITestCase):
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
        
        # Update board
        patch_resp = self.client.patch(f'/api/v1/admin/boards/{self.board.id}/', {
            "description": "Updated CBSE Description"
        }, format='json')
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data['description'], "Updated CBSE Description")

        # Delete board
        delete_resp = self.client.delete(f'/api/v1/admin/boards/{self.board.id}/')
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Board.objects.filter(id=self.board.id).exists())

    def test_admin_can_create_and_filter_classes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Create Class
        create_resp = self.client.post('/api/v1/admin/classes/', {
            "board": self.board.id,
            "name": "Class 12"
        }, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data['name'], "Class 12")
        self.assertEqual(create_resp.data['slug'], "class-12")

        # List Classes filtered by board
        list_resp = self.client.get(f'/api/v1/admin/classes/?board_id={self.board.id}')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 2)  # Class 10 and Class 12

    def test_student_forbidden_from_admin_boards_and_classes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.student_token}')
        
        # Student attempting to access admin boards receives 403
        board_resp = self.client.get('/api/v1/admin/boards/')
        self.assertEqual(board_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Student attempting to create class receives 403
        class_resp = self.client.post('/api/v1/admin/classes/', {
            "board": self.board.id,
            "name": "Unauthorized Class"
        }, format='json')
        self.assertEqual(class_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_request_rejected(self):
        self.client.credentials()
        resp = self.client.get('/api/v1/admin/boards/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

from django.test import TestCase
from django.db import transaction
from django.db.utils import IntegrityError
from .models import Board, ClassLevel, Subject, Chapter


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

    def test_model_creation_and_string_representations(self):
        self.assertEqual(str(self.board), "CBSE")
        self.assertEqual(str(self.academic_class), "CBSE - Class 10")
        self.assertEqual(str(self.subject), "CBSE - Class 10 - Mathematics")
        self.assertEqual(str(self.chapter), "Mathematics - Ch 1: Real Numbers")

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

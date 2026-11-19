from django.db import models


class Board(models.Model):
    """
    Represents an educational board (e.g. CBSE, ICSE, State Board).
    Top-level tier of the curriculum hierarchy.
    """
    name = models.CharField(max_length=100, help_text="Board name, e.g., CBSE")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly slug")
    description = models.TextField(blank=True, null=True, help_text="Optional description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'boards'
        ordering = ['name']
        verbose_name = 'Board'
        verbose_name_plural = 'Boards'

    def __str__(self):
        return self.name


class ClassLevel(models.Model):
    """
    Represents an academic class level under a board (e.g. Class 10, Class 12).
    Mapped to the 'classes' table in MySQL.
    """
    board = models.ForeignKey(
        Board,
        on_delete=models.CASCADE,
        related_name='classes',
        help_text="Board this class belongs to"
    )
    name = models.CharField(max_length=50, help_text="Class name, e.g., Class 10")
    slug = models.SlugField(max_length=50, help_text="URL-friendly slug")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'classes'
        unique_together = ('board', 'slug')
        ordering = ['board', 'name']
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return f"{self.board.name} - {self.name}"


class Subject(models.Model):
    """
    Represents an academic subject under a class (e.g. Mathematics, Physics).
    """
    academic_class = models.ForeignKey(
        ClassLevel,
        on_delete=models.CASCADE,
        db_column='class_id',
        related_name='subjects',
        help_text="Class this subject belongs to"
    )
    name = models.CharField(max_length=100, help_text="Subject name, e.g., Mathematics")
    slug = models.SlugField(max_length=100, help_text="URL-friendly slug")
    thumbnail_url = models.CharField(max_length=255, blank=True, null=True, help_text="Subject icon or thumbnail URL")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subjects'
        unique_together = ('academic_class', 'slug')
        ordering = ['academic_class', 'name']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'

    def __str__(self):
        return f"{self.academic_class} - {self.name}"


class Chapter(models.Model):
    """
    Represents a specific chapter or topic under a subject.
    Can be designated as a free sample.
    """
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='chapters',
        help_text="Subject this chapter belongs to"
    )
    chapter_number = models.PositiveIntegerField(help_text="Sequential chapter number within subject")
    title = models.CharField(max_length=200, help_text="Chapter title, e.g., Quadratic Equations")
    slug = models.SlugField(max_length=200, help_text="URL-friendly slug")
    is_free_sample = models.BooleanField(
        default=False,
        help_text="Designates this chapter as a free preview available without purchase"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chapters'
        unique_together = (
            ('subject', 'chapter_number'),
            ('subject', 'slug'),
        )
        ordering = ['subject', 'chapter_number']
        verbose_name = 'Chapter'
        verbose_name_plural = 'Chapters'

    def __str__(self):
        return f"{self.subject.name} - Ch {self.chapter_number}: {self.title}"

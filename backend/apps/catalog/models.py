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

    def clean(self):
        super().clean()
        if self.is_free_sample and getattr(self, 'subject_id', None):
            qs = Chapter.objects.filter(subject_id=self.subject_id, is_free_sample=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'is_free_sample': 'Only one chapter per subject can be marked as a free sample.'
                })

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title) or f"chapter-{self.chapter_number}"
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subject.name} - Ch {self.chapter_number}: {self.title}"


class Material(models.Model):
    """
    Represents protected educational study notes (typically PDF files)
    associated with a chapter. Stored in a private, non-public directory.
    """
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='materials',
        help_text="Chapter this study material belongs to"
    )
    title = models.CharField(max_length=200, help_text="Material title, e.g., Formula Sheet & Notes")
    file_path = models.CharField(
        max_length=500,
        help_text="Internal protected file system path. Never exposed directly as a public URL."
    )
    file_size_bytes = models.BigIntegerField(default=0, help_text="File size in bytes")
    mime_type = models.CharField(max_length=50, default='application/pdf', help_text="MIME type, e.g. application/pdf")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'materials'
        ordering = ['chapter', 'title']
        verbose_name = 'Study Material'
        verbose_name_plural = 'Study Materials'

    def __str__(self):
        return f"{self.chapter.title} - {self.title}"


class PromoBanner(models.Model):
    """
    Custom promotional hero banners displayed across catalog scopes (e.g. Class, Board, or Global).
    Administrators can create, edit, toggle visibility, and customize title, description, badge, and CTA buttons.
    """
    title = models.CharField(max_length=255, help_text="Headline text for the banner")
    badge_text = models.CharField(max_length=100, default="⚡ Best Value: Full Class Pass", help_text="Pill badge label")
    description = models.TextField(help_text="Body description detailing inclusions or promotional pitch")
    academic_class = models.ForeignKey(
        ClassLevel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='promo_banners',
        help_text="Associated class (optional: leaves banner as global if blank)"
    )
    monthly_pass_text = models.CharField(max_length=100, default="Monthly Pass (₹299 / 30 Days)")
    annual_pass_text = models.CharField(max_length=100, default="Annual Pass (₹2,499 / 365 Days)")
    monthly_pass_url = models.CharField(max_length=255, blank=True, null=True)
    annual_pass_url = models.CharField(max_length=255, blank=True, null=True)
    gradient_theme = models.CharField(max_length=100, default="from-indigo-900 via-indigo-800 to-purple-900")
    is_active = models.BooleanField(default=True, help_text="Controls banner display in store")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'promo_banners'
        ordering = ['-created_at']
        verbose_name = 'Promotional Banner'
        verbose_name_plural = 'Promotional Banners'

    def __str__(self):
        return f"Banner: {self.title} ({'Active' if self.is_active else 'Disabled'})"



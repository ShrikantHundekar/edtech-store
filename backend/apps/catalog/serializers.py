from rest_framework import serializers
from django.utils.text import slugify
from .models import Board, ClassLevel, Subject, Chapter, Material


class BoardSerializer(serializers.ModelSerializer):
    classes_count = serializers.IntegerField(source='classes.count', read_only=True)
    slug = serializers.SlugField(required=False)

    class Meta:
        model = Board
        fields = ('id', 'name', 'slug', 'description', 'classes_count', 'created_at', 'updated_at')

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if not data.get('slug') and data.get('name'):
            data['slug'] = slugify(data['name'])
        return super().to_internal_value(data)


class ClassLevelSerializer(serializers.ModelSerializer):
    board_name = serializers.CharField(source='board.name', read_only=True)
    subjects_count = serializers.IntegerField(source='subjects.count', read_only=True)
    slug = serializers.SlugField(required=False)

    class Meta:
        model = ClassLevel
        fields = ('id', 'board', 'board_name', 'name', 'slug', 'subjects_count', 'created_at', 'updated_at')

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if not data.get('slug') and data.get('name'):
            data['slug'] = slugify(data['name'])
        return super().to_internal_value(data)


class SubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='academic_class.name', read_only=True)
    board_name = serializers.CharField(source='academic_class.board.name', read_only=True)
    chapters_count = serializers.IntegerField(source='chapters.count', read_only=True)
    slug = serializers.SlugField(required=False)

    class Meta:
        model = Subject
        fields = (
            'id',
            'academic_class',
            'class_name',
            'board_name',
            'name',
            'slug',
            'thumbnail_url',
            'chapters_count',
            'created_at',
            'updated_at',
        )

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if not data.get('slug') and data.get('name'):
            data['slug'] = slugify(data['name'])
        return super().to_internal_value(data)


class ChapterSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    materials_count = serializers.IntegerField(source='materials.count', read_only=True)
    slug = serializers.SlugField(required=False)

    class Meta:
        model = Chapter
        fields = (
            'id',
            'subject',
            'subject_name',
            'chapter_number',
            'title',
            'slug',
            'is_free_sample',
            'materials_count',
            'created_at',
            'updated_at',
        )

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if not data.get('slug') and data.get('title'):
            data['slug'] = slugify(data['title'])
        return super().to_internal_value(data)


class MaterialSerializer(serializers.ModelSerializer):
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)

    class Meta:
        model = Material
        fields = (
            'id',
            'chapter',
            'chapter_title',
            'title',
            'file_path',
            'file_size_bytes',
            'mime_type',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'file_size_bytes', 'mime_type')


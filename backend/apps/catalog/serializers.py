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

from django.contrib import admin
from .models import Board, ClassLevel, Subject, Chapter


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'board', 'slug', 'created_at')
    list_filter = ('board',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_class', 'slug', 'created_at')
    list_filter = ('academic_class__board', 'academic_class')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('chapter_number', 'title', 'subject', 'is_free_sample', 'created_at')
    list_filter = ('is_free_sample', 'subject__academic_class', 'subject')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}

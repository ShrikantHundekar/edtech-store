from django.urls import path
from .views import (
    PublicBoardListView,
    PublicBoardClassesListView,
    PublicClassSubjectsListView,
    PublicSubjectChaptersListView,
)

urlpatterns = [
    path('boards/', PublicBoardListView.as_view(), name='public_catalog_boards'),
    path('boards/<int:board_id>/classes/', PublicBoardClassesListView.as_view(), name='public_catalog_board_classes'),
    path('classes/<int:class_id>/subjects/', PublicClassSubjectsListView.as_view(), name='public_catalog_class_subjects'),
    path('subjects/<int:subject_id>/chapters/', PublicSubjectChaptersListView.as_view(), name='public_catalog_subject_chapters'),
]

from django.urls import path
from .views import (
    PublicBoardListView,
    PublicBoardClassesListView,
    PublicClassSubjectsListView,
    PublicSubjectChaptersListView,
    PublicChapterDetailView,
    CatalogSearchView,
    MaterialStreamView,
    PublicPromoBannerListView,
)

urlpatterns = [
    path('banners/', PublicPromoBannerListView.as_view(), name='public_catalog_banners'),
    path('boards/', PublicBoardListView.as_view(), name='public_catalog_boards'),
    path('boards/<int:board_id>/classes/', PublicBoardClassesListView.as_view(), name='public_catalog_board_classes'),
    path('classes/<int:class_id>/subjects/', PublicClassSubjectsListView.as_view(), name='public_catalog_class_subjects'),
    path('subjects/<int:subject_id>/chapters/', PublicSubjectChaptersListView.as_view(), name='public_catalog_subject_chapters'),
    path('chapters/<int:chapter_id>/', PublicChapterDetailView.as_view(), name='public_catalog_chapter_detail'),
    path('materials/<int:material_id>/stream/', MaterialStreamView.as_view(), name='catalog_material_stream'),
    path('search/', CatalogSearchView.as_view(), name='public_catalog_search'),
]

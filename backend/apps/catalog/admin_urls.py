from rest_framework.routers import DefaultRouter
from .views import (
    AdminBoardViewSet,
    AdminClassViewSet,
    AdminSubjectViewSet,
    AdminChapterViewSet,
    AdminPromoBannerViewSet,
)

router = DefaultRouter()
router.register('boards', AdminBoardViewSet, basename='admin-board')
router.register('classes', AdminClassViewSet, basename='admin-class')
router.register('subjects', AdminSubjectViewSet, basename='admin-subject')
router.register('chapters', AdminChapterViewSet, basename='admin-chapter')
router.register('banners', AdminPromoBannerViewSet, basename='admin-banner')

urlpatterns = router.urls

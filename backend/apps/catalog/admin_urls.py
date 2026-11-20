from rest_framework.routers import DefaultRouter
from .views import AdminBoardViewSet, AdminClassViewSet

router = DefaultRouter()
router.register('boards', AdminBoardViewSet, basename='admin-board')
router.register('classes', AdminClassViewSet, basename='admin-class')

urlpatterns = router.urls

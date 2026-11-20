from django.urls import path
from .views import MaterialDetailView, MaterialStreamView

urlpatterns = [
    path('<int:material_id>/', MaterialDetailView.as_view(), name='material_detail'),
    path('<int:material_id>/stream/', MaterialStreamView.as_view(), name='material_stream'),
]

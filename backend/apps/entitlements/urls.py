from django.urls import path
from .views import StudentLibraryView

urlpatterns = [
    path('my-library/', StudentLibraryView.as_view(), name='student_library'),
]

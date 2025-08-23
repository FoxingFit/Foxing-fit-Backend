from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkoutGeneratorViewSet, WorkoutSessionViewSet

router = DefaultRouter()
router.register(r'sessions', WorkoutSessionViewSet, basename='workoutsession')
router.register(r'generate', WorkoutGeneratorViewSet, basename='generator')

urlpatterns = [
    path('', include(router.urls)),
]
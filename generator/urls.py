from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkoutGeneratorViewSet, WorkoutSessionViewSet, AudioViewSet

router = DefaultRouter()
router.register(r'sessions', WorkoutSessionViewSet, basename='workoutsession')
router.register(r'generate', WorkoutGeneratorViewSet, basename='generator')
router.register(r'audio', AudioViewSet, basename='audio')

urlpatterns = [
    path('', include(router.urls)),
]
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkoutScriptViewSet, 
    MotivationalQuoteViewSet, 
    ScriptCategoryViewSet,
    WorkoutTemplateViewSet
)

router = DefaultRouter()
router.register(r'scripts', WorkoutScriptViewSet, basename='workoutscript')
router.register(r'quotes', MotivationalQuoteViewSet, basename='motivationalquote')
router.register(r'categories', ScriptCategoryViewSet, basename='scriptcategory')
router.register(r'templates', WorkoutTemplateViewSet, basename='workouttemplate')

urlpatterns = [
    path('', include(router.urls)),
]

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory
from .serializers import (
    WorkoutScriptSerializer, 
    MotivationalQuoteSerializer, 
    ScriptCategorySerializer,
    WorkoutTemplateSerializer
)

class ScriptCategoryViewSet(viewsets.ModelViewSet):
    """Manage workout section types"""
    queryset = ScriptCategory.objects.filter(is_active=True)
    serializer_class = ScriptCategorySerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        return queryset.order_by('training_type', 'difficulty_level', 'display_name')

class WorkoutScriptViewSet(viewsets.ModelViewSet):
    """Manage workout scripts"""
    queryset = WorkoutScript.objects.filter(is_active=True)
    serializer_class = WorkoutScriptSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by training type
        training_type = self.request.query_params.get('type')
        if training_type:
            queryset = queryset.filter(type=training_type)
        
        # Filter by script category
        script_category_id = self.request.query_params.get('script_category_id')
        if script_category_id:
            queryset = queryset.filter(script_category_id=script_category_id)
        
        # Filter by goal
        goal = self.request.query_params.get('goal')
        if goal:
            queryset = queryset.filter(goal=goal)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        return queryset.order_by('type', 'script_category__display_name', 'title')
    
    @action(detail=False, methods=['get'])
    def available_categories(self, request):
        """Get available workout sections for a sport"""
        training_type = request.query_params.get('type')
        if not training_type:
            return Response({'error': 'type parameter required'}, status=400)
        
        script_categories = ScriptCategory.objects.filter(
            training_type=training_type,
            is_active=True
        ).order_by('display_name')
        
        return Response({
            'training_type': training_type,
            'script_categories': [
                {
                    'id': category.id,
                    'name': category.name,
                    'display_name': category.display_name,
                    'description': category.description,
                    'difficulty_level': category.difficulty_level
                }
                for category in script_categories
            ]
        })

class MotivationalQuoteViewSet(viewsets.ModelViewSet):
    """Manage motivational quotes"""
    queryset = MotivationalQuote.objects.filter(is_active=True)
    serializer_class = MotivationalQuoteSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        
        # Filter by exercise-specific vs general
        is_exercise_specific = self.request.query_params.get('is_exercise_specific')
        if is_exercise_specific is not None:
            queryset = queryset.filter(is_exercise_specific=is_exercise_specific.lower() == 'true')
        
        # Filter by target category
        target_category_id = self.request.query_params.get('target_category_id')
        if target_category_id:
            queryset = queryset.filter(target_category_id=target_category_id)
        
        return queryset.order_by('training_type', 'is_exercise_specific', 'target_category', 'quote_text')


class WorkoutTemplateViewSet(viewsets.ModelViewSet):
    """Manage workout templates"""
    queryset = WorkoutTemplate.objects.all()
    serializer_class = WorkoutTemplateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        return queryset.order_by('training_type', 'sequence_order')
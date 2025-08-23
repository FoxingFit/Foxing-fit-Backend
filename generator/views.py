from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from scripts.models import WorkoutTemplate, ScriptCategory
from .models import WorkoutSession
from .generator import IntelligentWorkoutGenerator  # Updated class name
from .serializers import WorkoutSessionSerializer

class WorkoutGeneratorViewSet(viewsets.ViewSet):
    """Smart workout generation with full admin control and sport-specific intelligence"""
    
    @action(detail=False, methods=['post'])
    def generate_workout(self, request):
        """
        Generate an intelligent workout with custom duration and full admin control
        
        UPDATED: Now uses IntelligentWorkoutGenerator with full admin control
        Body Parameters:
        - training_type (required): 'kickboxing', 'power_yoga', or 'calisthenics'
        - goal (optional): 'allround','strength', 'flexibility', (default: 'allround')
        - target_duration (optional): Target duration in minutes, 15-120 (default: 60.0)
        
        Returns:
        - Complete workout with admin-controlled special rounds
        - Time status analysis
        - Sport-specific additions summary based on admin template configuration
        """
        training_type = request.data.get('training_type')
        goal = request.data.get('goal', 'allround')
        target_duration = request.data.get('target_duration', 60.0)
        
        if not training_type:
            return Response({
                'error': 'training_type is required',
                'valid_types': ['kickboxing', 'power_yoga', 'calisthenics']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate training_type
        valid_types = ['kickboxing', 'power_yoga', 'calisthenics']
        if training_type not in valid_types:
            return Response({
                'error': f'Invalid training_type. Must be one of: {valid_types}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate goal
        valid_goals = ['allround', 'strength', 'flexibility']
        if goal not in valid_goals:
            return Response({
                'error': f'Invalid goal. Must be one of: {valid_goals}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate target_duration
        try:
            target_duration = float(target_duration)
            if target_duration < 15 or target_duration > 120:
                return Response({
                    'error': 'target_duration must be between 15 and 120 minutes'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                'error': 'target_duration must be a valid number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # UPDATED: Use new IntelligentWorkoutGenerator class name
            generator = IntelligentWorkoutGenerator()
            
            # UPDATED: Use new method name with admin control
            workout_data = generator.generate_workout_with_custom_duration(
                training_type, 
                goal, 
                target_duration
            )
            
            return Response({
                'success': True,
                'workout': workout_data,
                'message': f"Generated {workout_data['time_status']} workout with admin-controlled special rounds",
                'admin_control_applied': True,  # NEW: Indicate admin control is active
                'sport_intelligence_applied': workout_data['sport_specific_additions']
            })
            
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Workout generation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # generator/views.py - REPLACE THE preview_template METHOD ONLY

    @action(detail=False, methods=['get'])
    def preview_template(self, request):
        """
        Preview the workout template structure - FIXED response structure
        """
        training_type = request.query_params.get('training_type')
        
        # Get valid training types from ScriptCategory model
        valid_training_types = [choice[0] for choice in ScriptCategory.TRAINING_TYPES]
        
        if not training_type:
            return Response({
                'error': 'training_type parameter required',
                'valid_types': valid_training_types
            }, status=400)
        
        # Validate training_type using model data
        if training_type not in valid_training_types:
            return Response({
                'error': f'Invalid training_type. Must be one of: {valid_training_types}'
            }, status=400)
        
        try:
            # Get active templates for this sport
            templates = WorkoutTemplate.objects.filter(
                training_type=training_type
            ).order_by('sequence_order').prefetch_related('alternative_categories', 'primary_category')
            
            if not templates.exists():
                return Response({
                    'error': f'No workout templates found for {training_type}',
                    'suggestion': 'Run the setup command: python manage.py setup --setup-complete-system'
                }, status=404)
            
            template_data = []
            for template in templates:
                try:
                    # Safely get alternatives
                    alternatives = []
                    try:
                        alternatives = list(template.alternative_categories.values('id', 'display_name'))
                    except Exception:
                        alternatives = []
                    
                    # Build auto_additions_after in a generic way
                    auto_additions = []
                    warnings = []
                    
                    # Check for additional steps after this one using hasattr for safety
                    if hasattr(template, 'add_surprise_round_after') and template.add_surprise_round_after:
                        auto_additions.append({
                            'type': 'surprise_round',
                            'description': 'Surprise round will be added after this step',
                            'configured': True
                        })
                    
                    if hasattr(template, 'add_max_challenge_after') and template.add_max_challenge_after:
                        auto_additions.append({
                            'type': 'max_challenge',
                            'description': 'MAX challenge will be added after this step',
                            'configured': True
                        })
                    
                    if hasattr(template, 'add_vinyasa_transition_after') and template.add_vinyasa_transition_after:
                        vinyasa_type = getattr(template, 'vinyasa_type', None)
                        auto_additions.append({
                            'type': 'vinyasa_transition',
                            'vinyasa_type': vinyasa_type,
                            'description': f'Vinyasa transition ({vinyasa_type})' if vinyasa_type else 'Vinyasa transition',
                            'configured': True
                        })
                    
                    # Safely build template data
                    template_item = {
                        'sequence_order': template.sequence_order,
                        'primary_category': {
                            'id': template.primary_category.id,
                            'name': template.primary_category.name,
                            'display_name': template.primary_category.display_name
                        },
                        'alternatives': alternatives,
                        'is_required': template.is_required,
                        'is_active': True,  # Default to True if field doesn't exist
                        'auto_additions_after': auto_additions,
                        'placement_warnings': warnings
                    }
                    
                    template_data.append(template_item)
                    
                except Exception as template_error:
                    # Log individual template errors but continue processing
                    print(f"Error processing template {template.id}: {template_error}")
                    continue
            
            # Get training type display name from model choices
            training_type_display = None
            for choice_value, choice_display in ScriptCategory.TRAINING_TYPES:
                if choice_value == training_type:
                    training_type_display = choice_display
                    break
            
            # Return simple, generic structure
            return Response({
                'training_type': training_type,
                'training_type_display': training_type_display or training_type.replace('_', ' ').title(),
                'template_sequence': template_data,
                'sport_intelligence_summary': self._get_simple_sport_summary(training_type)
            })
            
        except Exception as e:
            print(f"Template preview error: {e}")
            return Response({
                'error': f'Failed to load workout template preview: {str(e)}',
                'training_type': training_type,
                'debug_info': f'Error type: {type(e).__name__}'
            }, status=500)

    def _get_simple_sport_summary(self, training_type):
        """Get generic sport summary without admin-specific language"""
        return {
            'training_type': training_type,
            'has_automation': True,
            'description': 'This sport supports automated additions between workout sections'
        }

# WorkoutSessionViewSet remains unchanged - no modifications needed for admin control
class WorkoutSessionViewSet(viewsets.ModelViewSet):
    """
    Complete CRUD operations for generated workouts
    NO CHANGES NEEDED - existing functionality works with new admin control system
    """
    queryset = WorkoutSession.objects.all()
    serializer_class = WorkoutSessionSerializer
    
    def get_queryset(self):
        """Enhanced filtering for workout sessions"""
        queryset = super().get_queryset()
        
        # Filter by training type
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type=training_type)
        
        # Filter by goal
        goal = self.request.query_params.get('goal')
        if goal:
            queryset = queryset.filter(goal=goal)
        
        # Filter by usage status
        is_used = self.request.query_params.get('is_used')
        if is_used is not None:
            queryset = queryset.filter(is_used=is_used.lower() == 'true')
        
        # Filter by duration range
        min_duration = self.request.query_params.get('min_duration')
        max_duration = self.request.query_params.get('max_duration')
        if min_duration:
            try:
                queryset = queryset.filter(total_duration__gte=float(min_duration))
            except ValueError:
                pass
        if max_duration:
            try:
                queryset = queryset.filter(total_duration__lte=float(max_duration))
            except ValueError:
                pass
        
        # Search in title and notes
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(notes__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def destroy(self, request, *args, **kwargs):
        """Delete a workout session with confirmation"""
        try:
            instance = self.get_object()
            session_title = instance.title
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': f'Workout session "{session_title}" deleted successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Failed to delete workout session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def mark_used(self, request, pk=None):
        """Mark a session as used/unused"""
        session = self.get_object()
        is_used = request.data.get('is_used', True)
        
        if not isinstance(is_used, bool):
            return Response({
                'error': 'is_used must be a boolean value'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session.is_used = is_used
        session.save(update_fields=['is_used'])
        
        return Response({
            'success': True,
            'message': f'Session marked as {"used" if is_used else "unused"}',
            'is_used': session.is_used,
            'session_title': session.title
        })
    
    @action(detail=True, methods=['post'])
    def update_notes(self, request, pk=None):
        """Update session notes"""
        session = self.get_object()
        notes = request.data.get('notes', '')
        
        if not isinstance(notes, str):
            return Response({
                'error': 'notes must be a string'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session.notes = notes
        session.save(update_fields=['notes'])
        
        return Response({
            'success': True,
            'message': 'Session notes updated successfully',
            'notes': session.notes,
            'session_title': session.title
        })
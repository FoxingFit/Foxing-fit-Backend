from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.http import FileResponse, Http404
from scripts.models import WorkoutTemplate, ScriptCategory
from .models import WorkoutSession, AudioPlaylist, AudioSegment
from .generator import IntelligentWorkoutGenerator  # Updated class name
from .serializers import WorkoutSessionSerializer, AudioPlaylistSerializer, AudioSegmentSerializer
from .audio_playlist_builder import AudioPlaylistBuilder
from .audio_merge_engine import AudioMergeEngine
import logging
import os

logger = logging.getLogger(__name__)

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



class AudioViewSet(viewsets.ViewSet):
    """
    Audio workout generation endpoints
    - Generate audio playlists from workout sessions
    - Merge audio segments into single MP3
    - Download individual segments
    """
    
    @action(detail=False, methods=['post'])
    def generate_playlist(self, request):
        """
        Generate audio playlist for a workout session
        
        Body Parameters:
        - workout_session_id (required): ID of the workout session
        - language (optional): 'nl' or 'en' (default: 'nl')
        
        Returns:
        - Audio playlist with segments and availability status
        """
        workout_session_id = request.data.get('workout_session_id')
        language = request.data.get('language', 'nl')
        
        if not workout_session_id:
            return Response({
                'error': 'workout_session_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if language not in ['nl', 'en']:
            return Response({
                'error': 'language must be "nl" or "en"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            workout_session = WorkoutSession.objects.get(id=workout_session_id)
        except WorkoutSession.DoesNotExist:
            return Response({
                'error': f'Workout session {workout_session_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Build audio playlist
            builder = AudioPlaylistBuilder()
            audio_playlist = builder.build_playlist(workout_session, language)
            
            if not audio_playlist:
                return Response({
                    'error': 'Failed to build audio playlist'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Serialize and return
            serializer = AudioPlaylistSerializer(audio_playlist, context={'request': request})
            
            return Response({
                'success': True,
                'playlist': serializer.data,
                'message': f'Audio playlist generated: {audio_playlist.available_segment_count}/{audio_playlist.segment_count} segments available'
            })
            
        except Exception as e:
            logger.error(f"Error generating audio playlist: {e}", exc_info=True)
            return Response({
                'error': f'Failed to generate audio playlist: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def merge_playlist(self, request):
        """
        Merge audio playlist into single MP3 file
        
        Body Parameters:
        - playlist_id (required): ID of the audio playlist
        
        Returns:
        - Download URL for merged MP3 file
        """
        playlist_id = request.data.get('playlist_id')
        
        if not playlist_id:
            return Response({
                'error': 'playlist_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            audio_playlist = AudioPlaylist.objects.get(id=playlist_id)
        except AudioPlaylist.DoesNotExist:
            return Response({
                'error': f'Audio playlist {playlist_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Merge audio
            merge_engine = AudioMergeEngine()
            success, file_path, error_message = merge_engine.merge_playlist(audio_playlist)
            
            if not success:
                return Response({
                    'error': error_message or 'Failed to merge audio playlist'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Build download URL
            filename = os.path.basename(file_path)
            download_url = request.build_absolute_uri(f'/media/merged_audio/{filename}')
            
            # Get file size
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            return Response({
                'success': True,
                'download_url': download_url,
                'filename': filename,
                'duration': audio_playlist.total_duration,
                'file_size': file_size,
                'message': 'Audio playlist merged successfully'
            })
            
        except Exception as e:
            logger.error(f"Error merging audio playlist: {e}", exc_info=True)
            return Response({
                'error': f'Failed to merge audio playlist: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def download_segment(self, request, pk=None):
        """
        Download individual audio segment
        
        URL Parameters:
        - pk: ID of the audio segment
        
        Returns:
        - Audio file download
        """
        try:
            segment = AudioSegment.objects.get(id=pk)
        except AudioSegment.DoesNotExist:
            raise Http404("Audio segment not found")
        
        if not segment.is_available:
            return Response({
                'error': 'Audio not available for this segment'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get audio file from workout script
        workout_script = segment.session_script.workout_script
        language = segment.audio_playlist.language
        audio_file = workout_script.get_audio_file(language)
        
        if not audio_file:
            return Response({
                'error': 'Audio file not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Generate filename
            filename = f"{segment.sequence_order}_{workout_script.title}_{language}.mp3"
            filename = filename.replace(' ', '_').replace('/', '_')
            
            # Return file response
            response = FileResponse(audio_file.open('rb'), content_type='audio/mpeg')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            logger.error(f"Error downloading audio segment: {e}", exc_info=True)
            return Response({
                'error': f'Failed to download audio segment: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def get_playlist(self, request, pk=None):
        """
        Get audio playlist details
        
        URL Parameters:
        - pk: ID of the audio playlist
        
        Returns:
        - Complete playlist with segments
        """
        try:
            audio_playlist = AudioPlaylist.objects.get(id=pk)
        except AudioPlaylist.DoesNotExist:
            return Response({
                'error': f'Audio playlist {pk} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AudioPlaylistSerializer(audio_playlist, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def list_playlists(self, request):
        """
        List all audio playlists with optional filtering
        
        Query Parameters:
        - workout_session_id: Filter by workout session
        - language: Filter by language ('nl' or 'en')
        
        Returns:
        - List of audio playlists
        """
        queryset = AudioPlaylist.objects.all()
        
        # Filter by workout session
        workout_session_id = request.query_params.get('workout_session_id')
        if workout_session_id:
            queryset = queryset.filter(workout_session_id=workout_session_id)
        
        # Filter by language
        language = request.query_params.get('language')
        if language:
            queryset = queryset.filter(language=language)
        
        queryset = queryset.order_by('-created_at')
        
        serializer = AudioPlaylistSerializer(queryset, many=True, context={'request': request})
        return Response({
            'count': queryset.count(),
            'playlists': serializer.data
        })

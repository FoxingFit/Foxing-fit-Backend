"""
Audio Playlist Builder Service

Builds audio playlists from workout sessions
- Reads SessionScript sequence and creates AudioSegments
- Handles missing audio gracefully
- Calculates total duration including pauses
"""

import logging
from .models import AudioPlaylist, AudioSegment

logger = logging.getLogger(__name__)


class AudioPlaylistBuilder:
    """
    Builds audio playlists for workout sessions
    Operates in read-only mode on workout data
    """
    
    STANDARDIZED_PAUSE_SECONDS = 2.0  # 2-second pause between segments
    DURATION_WARNING_THRESHOLD = 0.10  # Warn if audio differs by more than 10%
    
    def build_playlist(self, workout_session, language='nl'):
        """
        Build audio playlist for a workout session
        
        Args:
            workout_session: WorkoutSession instance
            language: 'nl' or 'en'
            
        Returns:
            AudioPlaylist instance
        """
        try:
            # Get all session scripts in order
            session_scripts = workout_session.session_scripts.all().order_by('sequence_order')
            
            if not session_scripts.exists():
                logger.warning(f"No session scripts found for workout session {workout_session.id}")
                return None
            
            # Create or get existing playlist
            audio_playlist, created = AudioPlaylist.objects.get_or_create(
                workout_session=workout_session,
                language=language,
                defaults={
                    'total_duration': 0.0,
                    'segment_count': 0,
                    'available_segment_count': 0
                }
            )
            
            # If playlist already exists, just return it instead of rebuilding
            if not created:
                logger.info(f"Playlist {audio_playlist.id} already exists for session {workout_session.id}, returning existing playlist")
                return audio_playlist
            
            # Only create segments for new playlists
            
            # Create audio segments
            segments_created = self.create_audio_segments(audio_playlist, session_scripts, language)
            
            # Calculate total duration
            total_duration = self.calculate_total_duration(audio_playlist.segments.all())
            
            # Update playlist metadata
            audio_playlist.total_duration = total_duration
            audio_playlist.segment_count = session_scripts.count()
            audio_playlist.available_segment_count = segments_created
            audio_playlist.save()
            
            # Validate duration accuracy
            self.validate_duration_accuracy(audio_playlist, workout_session)
            
            logger.info(f"Built audio playlist {audio_playlist.id} for session {workout_session.id}: {segments_created}/{session_scripts.count()} segments available")
            
            return audio_playlist
            
        except Exception as e:
            logger.error(f"Error building audio playlist: {e}", exc_info=True)
            return None
    
    def create_audio_segments(self, audio_playlist, session_scripts, language):
        """
        Create AudioSegment instances for each SessionScript
        Skips segments without audio and logs warnings
        
        Args:
            audio_playlist: AudioPlaylist instance
            session_scripts: QuerySet of SessionScript instances
            language: 'nl' or 'en'
            
        Returns:
            Number of segments with available audio
        """
        available_count = 0
        
        for session_script in session_scripts:
            workout_script = session_script.workout_script
            
            # Check if audio is available
            has_audio = workout_script.has_audio(language)
            audio_file = workout_script.get_audio_file(language) if has_audio else None
            
            # Get audio duration
            if language == 'nl':
                audio_duration = workout_script.audio_duration_nl
            else:
                audio_duration = workout_script.audio_duration_en
            
            # Determine pause after this segment
            # Last segment gets no pause
            is_last = session_script.sequence_order == session_scripts.count()
            pause_after = 0.0 if is_last else self.STANDARDIZED_PAUSE_SECONDS
            
            # Create audio segment
            AudioSegment.objects.create(
                audio_playlist=audio_playlist,
                session_script=session_script,
                sequence_order=session_script.sequence_order,
                audio_file=audio_file,
                duration=audio_duration,
                is_available=has_audio,
                pause_after=pause_after
            )
            
            if has_audio:
                available_count += 1
            else:
                logger.warning(
                    f"Missing {language.upper()} audio for script '{workout_script.title}' "
                    f"(ID: {workout_script.id}) in session {audio_playlist.workout_session.id}"
                )
        
        return available_count
    
    def calculate_total_duration(self, audio_segments):
        """
        Calculate total duration including pauses
        Duration = sum(segment.duration) + sum(segment.pause_after)
        
        Args:
            audio_segments: QuerySet of AudioSegment instances
            
        Returns:
            Total duration in minutes
        """
        total_audio_duration = 0.0
        total_pause_duration = 0.0
        
        for segment in audio_segments:
            if segment.is_available and segment.duration:
                total_audio_duration += segment.duration
            
            # Convert pause from seconds to minutes
            total_pause_duration += segment.pause_after / 60.0
        
        total_duration = total_audio_duration + total_pause_duration
        return round(total_duration, 1)
    
    def validate_duration_accuracy(self, audio_playlist, workout_session):
        """
        Compare audio duration to text duration
        Warn if difference exceeds threshold
        
        Args:
            audio_playlist: AudioPlaylist instance
            workout_session: WorkoutSession instance
        """
        if not audio_playlist.is_complete():
            logger.info(
                f"Audio playlist {audio_playlist.id} is incomplete "
                f"({audio_playlist.get_completeness_percentage():.0f}% complete), "
                f"skipping duration validation"
            )
            return
        
        text_duration = workout_session.total_duration
        audio_duration = audio_playlist.total_duration
        
        if text_duration == 0:
            logger.warning(f"Workout session {workout_session.id} has zero duration")
            return
        
        difference = abs(audio_duration - text_duration)
        percentage_diff = (difference / text_duration)
        
        if percentage_diff > self.DURATION_WARNING_THRESHOLD:
            logger.warning(
                f"Audio playlist {audio_playlist.id} duration ({audio_duration:.1f}min) "
                f"differs from text duration ({text_duration:.1f}min) by {percentage_diff*100:.1f}%"
            )
        else:
            logger.info(
                f"Audio playlist {audio_playlist.id} duration matches text duration "
                f"(difference: {percentage_diff*100:.1f}%)"
            )
    
    def rebuild_playlist(self, audio_playlist):
        """
        Rebuild an existing audio playlist
        Useful when audio files are added or updated
        
        Args:
            audio_playlist: AudioPlaylist instance
            
        Returns:
            Updated AudioPlaylist instance
        """
        workout_session = audio_playlist.workout_session
        language = audio_playlist.language
        
        logger.info(f"Rebuilding audio playlist {audio_playlist.id}")
        
        return self.build_playlist(workout_session, language)

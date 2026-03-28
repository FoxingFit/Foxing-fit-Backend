"""
Audio Playlist Builder - Creates audio playlists from workout sessions
Filters quotes: max 1 per position, respects sport-specific rules
"""

import logging
import random
from .models import AudioPlaylist, AudioSegment, AudioQuoteSegment, SessionQuote
from scripts.models import MotivationalQuote

logger = logging.getLogger(__name__)


class AudioPlaylistBuilder:
    """Builds audio playlists with intelligent quote filtering"""
    
    STANDARDIZED_PAUSE_SECONDS = 2.0
    DURATION_WARNING_THRESHOLD = 0.10
    
    def build_playlist(self, workout_session, language='nl'):
        """
        Build audio playlist with filtered quotes
        Rules: Max 1 quote per position, skip first/last, apply sport rules
        """
        try:
            session_scripts = workout_session.session_scripts.all().order_by('sequence_order')
            
            if not session_scripts.exists():
                logger.warning(f"No scripts for session {workout_session.id}")
                return None
            
            session_quotes = workout_session.session_quotes.all().order_by('sequence_order')
            
            # Get or create playlist
            audio_playlist, created = AudioPlaylist.objects.get_or_create(
                workout_session=workout_session,
                language=language,
                defaults={'total_duration': 0.0, 'segment_count': 0, 'available_segment_count': 0}
            )
            
            if not created:
                logger.info(f"Playlist {audio_playlist.id} exists, returning")
                return audio_playlist
            
            # Create segments
            script_segments_created = self.create_audio_segments(audio_playlist, session_scripts, language)
            quote_segments_created = self.create_audio_quote_segments_filtered(
                audio_playlist, session_scripts, session_quotes, language
            )
            
            # Calculate duration
            all_segments = list(audio_playlist.segments.all()) + list(audio_playlist.quote_segments.all())
            total_duration = self.calculate_total_duration_mixed(all_segments)
            
            # Update metadata
            audio_playlist.total_duration = total_duration
            audio_playlist.segment_count = session_scripts.count() + quote_segments_created
            audio_playlist.available_segment_count = script_segments_created + quote_segments_created
            audio_playlist.save()
            
            self.validate_duration_accuracy(audio_playlist, workout_session)
            
            logger.info(
                f"Built playlist {audio_playlist.id}: "
                f"{script_segments_created}/{session_scripts.count()} scripts, "
                f"{quote_segments_created} quotes"
            )
            
            return audio_playlist
            
        except Exception as e:
            logger.error(f"Error building playlist: {e}", exc_info=True)
            return None
    
    def create_audio_quote_segments_filtered(self, audio_playlist, session_scripts, session_quotes, language):
        """
        Create quote segments with filtering:
        - Max 1 per position (if multiple, use first)
        - Skip first/last scripts
        """
        available_count = 0
        session_scripts_list = list(session_scripts)
        total_scripts = len(session_scripts_list)

        logger.info(f"Creating quote segments (max 1 per position)")
        logger.info(f"Found {session_quotes.count()} quotes in text")
        
        # Group quotes by script
        quotes_by_script = {}
        for session_quote in session_quotes:
            script_id = session_quote.inserted_after_script.id
            if script_id not in quotes_by_script:
                quotes_by_script[script_id] = []
            quotes_by_script[script_id].append(session_quote)
        
        # Process each position
        for i, session_script in enumerate(session_scripts_list):
            workout_script = session_script.workout_script
            
            # Skip first/last
            if i == 0:
                logger.info(f"Skipping first: {workout_script.title}")
                continue
            if i == total_scripts - 1:
                logger.info(f"Skipping last: {workout_script.title}")
                continue
            
            # Check for quotes
            if session_script.id not in quotes_by_script:
                continue
            
            quotes_for_this_script = quotes_by_script[session_script.id]
            
            # Use first quote only
            if len(quotes_for_this_script) > 1:
                logger.info(f"'{workout_script.title}' has {len(quotes_for_this_script)} quotes, using first")
            
            session_quote = quotes_for_this_script[0]
            motivational_quote = session_quote.motivational_quote
            
            # Get audio
            has_audio = motivational_quote.has_audio(language)
            audio_file = motivational_quote.get_audio_file(language) if has_audio else None
            audio_duration = motivational_quote.get_audio_duration(language)
            
            # Create segment
            AudioQuoteSegment.objects.create(
                audio_playlist=audio_playlist,
                session_quote=session_quote,
                sequence_order=session_quote.sequence_order,
                audio_file=audio_file,
                duration=audio_duration,
                is_available=has_audio,
                pause_after=self.STANDARDIZED_PAUSE_SECONDS
            )
            
            if has_audio:
                available_count += 1
                logger.info(f"Added quote after '{workout_script.title}': {motivational_quote.quote_text[:50]}...")
            else:
                logger.warning(f"No {language} audio: {motivational_quote.quote_text[:50]}...")
        
        logger.info(f"Created {available_count} quote segments (filtered from {session_quotes.count()})")
        return available_count
    
    def create_audio_segments(self, audio_playlist, session_scripts, language):
        """Create audio segments for scripts"""
        available_count = 0
        
        for session_script in session_scripts:
            workout_script = session_script.workout_script
            
            # Get audio
            has_audio = workout_script.has_audio(language)
            audio_file = workout_script.get_audio_file(language) if has_audio else None
            audio_duration = workout_script.audio_duration_nl if language == 'nl' else workout_script.audio_duration_en
            
            # Pause (no pause after last)
            is_last = session_script.sequence_order == session_scripts.count()
            pause_after = 0.0 if is_last else self.STANDARDIZED_PAUSE_SECONDS
            
            # Create segment
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
                logger.warning(f"Missing {language} audio: '{workout_script.title}' (ID: {workout_script.id})")
        
        return available_count
    
    def calculate_total_duration_mixed(self, mixed_segments):
        """Calculate total duration (audio + pauses) in minutes"""
        total_audio = sum(s.duration for s in mixed_segments if s.is_available and s.duration)
        total_pause = sum(s.pause_after for s in mixed_segments) / 60.0  # Convert to minutes
        return round(total_audio + total_pause, 1)
    
    def validate_duration_accuracy(self, audio_playlist, workout_session):
        """Compare audio duration to text duration, warn if mismatch"""
        if not audio_playlist.is_complete():
            logger.info(f"Playlist {audio_playlist.id} incomplete ({audio_playlist.get_completeness_percentage():.0f}%), skipping validation")
            return
        
        text_duration = workout_session.total_duration
        audio_duration = audio_playlist.total_duration
        
        if text_duration == 0:
            logger.warning(f"Session {workout_session.id} has zero duration")
            return
        
        percentage_diff = abs(audio_duration - text_duration) / text_duration
        
        if percentage_diff > self.DURATION_WARNING_THRESHOLD:
            logger.warning(f"Playlist {audio_playlist.id} duration mismatch: {audio_duration:.1f}min vs {text_duration:.1f}min ({percentage_diff*100:.1f}%)")
        else:
            logger.info(f"Playlist {audio_playlist.id} duration OK (diff: {percentage_diff*100:.1f}%)")
    
    def rebuild_playlist(self, audio_playlist):
        """Rebuild existing playlist (useful when audio files updated)"""
        logger.info(f"Rebuilding playlist {audio_playlist.id}")
        return self.build_playlist(audio_playlist.workout_session, audio_playlist.language)

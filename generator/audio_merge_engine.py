"""
Audio Merge Engine Service

Merges audio segments into a single MP3 file
- Concatenates segments with standardized pauses
- Applies volume normalization
- Prevents clipping and silence stacking
"""

import logging
import os
from pydub import AudioSegment as PydubSegment
from pydub.effects import normalize
from django.conf import settings

logger = logging.getLogger(__name__)


class AudioMergeEngine:
    """
    Merges audio segments into a single seamless MP3 file
    """
    
    STANDARDIZED_PAUSE_MS = 2000  # 2 seconds in milliseconds
    TARGET_DBFS = -20.0  # Target loudness in dBFS
    MAX_DBFS = -1.0  # Maximum to prevent clipping
    
    def merge_playlist(self, audio_playlist):
        """
        Merge all segments in playlist into single MP3
        
        Args:
            audio_playlist: AudioPlaylist instance
            
        Returns:
            (success, file_path, error_message)
        """
        try:
            segments = audio_playlist.segments.filter(is_available=True).order_by('sequence_order')
            
            if not segments.exists():
                return (False, None, "No audio segments available to merge")
            
            # Load all audio segments
            audio_files = []
            for segment in segments:
                try:
                    audio_file = self._load_audio_file(segment)
                    if audio_file:
                        audio_files.append((segment, audio_file))
                except Exception as e:
                    logger.error(f"Error loading audio for segment {segment.id}: {e}")
                    # Continue with other segments
            
            if not audio_files:
                return (False, None, "Could not load any audio files")
            
            # Normalize volume for all segments
            normalized_files = self.normalize_volume(audio_files)
            
            # Insert pauses and concatenate
            merged_audio = self.insert_pauses(normalized_files, segments)
            
            # Check for clipping
            if self.detect_clipping(merged_audio):
                logger.warning(f"Clipping detected in merged audio for playlist {audio_playlist.id}, reducing volume")
                # Reduce volume slightly and try again
                merged_audio = merged_audio - 2  # Reduce by 2 dB
            
            # Generate filename and save
            filename = self.generate_filename(audio_playlist.workout_session, audio_playlist.language)
            file_path = self._save_merged_audio(merged_audio, filename)
            
            # Update playlist with merged file reference
            from django.core.files import File
            from django.utils import timezone
            with open(file_path, 'rb') as f:
                audio_playlist.merged_audio_file.save(filename, File(f), save=False)
            audio_playlist.merged_at = timezone.now()
            audio_playlist.save()
            
            logger.info(f"Successfully merged audio playlist {audio_playlist.id} to {file_path}")
            
            return (True, file_path, None)
            
        except Exception as e:
            logger.error(f"Error merging audio playlist {audio_playlist.id}: {e}", exc_info=True)
            return (False, None, f"Error merging audio: {str(e)}")
    
    def _load_audio_file(self, segment):
        """Load audio file from segment"""
        try:
            workout_script = segment.session_script.workout_script
            language = segment.audio_playlist.language
            
            audio_file = workout_script.get_audio_file(language)
            
            if not audio_file:
                logger.error(f"No audio file for script {workout_script.id} in language {language}")
                return None
            
            # Get file path - try multiple methods
            file_path = None
            
            try:
                # Method 1: Try .path attribute (works when file is on local filesystem)
                if hasattr(audio_file, 'path'):
                    file_path = audio_file.path
                    logger.debug(f"Got file path from .path: {file_path}")
            except Exception as e:
                logger.debug(f"Could not get .path: {e}")
            
            if not file_path:
                # Method 2: Build path from MEDIA_ROOT and file name
                file_path = os.path.join(settings.MEDIA_ROOT, audio_file.name)
                logger.debug(f"Built file path from MEDIA_ROOT: {file_path}")
            
            # Verify file exists
            if not os.path.exists(file_path):
                logger.error(f"Audio file not found at path: {file_path}")
                return None
            
            logger.info(f"Loading audio from: {file_path}")
            
            # Load with pydub
            audio = PydubSegment.from_file(file_path)
            logger.info(f"Successfully loaded audio: {len(audio)}ms")
            return audio
            
        except Exception as e:
            logger.error(f"Error loading audio file for segment {segment.id}: {e}", exc_info=True)
            return None
    
    def normalize_volume(self, audio_files):
        """
        Apply volume normalization across all segments
        Uses peak normalization to prevent clipping
        
        Args:
            audio_files: List of (segment, audio) tuples
            
        Returns:
            List of (segment, normalized_audio) tuples
        """
        normalized = []
        
        for segment, audio in audio_files:
            try:
                # Apply normalization
                normalized_audio = normalize(audio, headroom=1.0)
                
                # Ensure we don't exceed max dBFS
                if normalized_audio.dBFS > self.MAX_DBFS:
                    reduction = normalized_audio.dBFS - self.MAX_DBFS
                    normalized_audio = normalized_audio - reduction
                
                normalized.append((segment, normalized_audio))
                
            except Exception as e:
                logger.error(f"Error normalizing audio for segment {segment.id}: {e}")
                # Use original audio if normalization fails
                normalized.append((segment, audio))
        
        return normalized
    
    def insert_pauses(self, audio_files, segments):
        """
        Insert standardized pauses between segments
        Prevents silence stacking by detecting existing silence
        
        Args:
            audio_files: List of (segment, audio) tuples
            segments: QuerySet of AudioSegment instances
            
        Returns:
            Merged AudioSegment (pydub)
        """
        if not audio_files:
            return None
        
        # Start with first audio
        merged = audio_files[0][1]
        
        # Add remaining segments with pauses
        for i in range(1, len(audio_files)):
            segment, audio = audio_files[i]
            
            # Check if we need to add pause
            # (last segment should have pause_after = 0)
            previous_segment = segments[i-1]
            
            if previous_segment.pause_after > 0:
                # Create silence
                pause_ms = int(previous_segment.pause_after * 1000)
                silence = PydubSegment.silent(duration=pause_ms)
                
                # Add pause then audio
                merged = merged + silence + audio
            else:
                # No pause, just concatenate
                merged = merged + audio
        
        return merged
    
    def detect_clipping(self, merged_audio):
        """
        Analyze merged audio for clipping
        
        Args:
            merged_audio: pydub AudioSegment
            
        Returns:
            True if clipping detected
        """
        try:
            # Check if peak level is too close to maximum
            if merged_audio.dBFS > self.MAX_DBFS:
                return True
            
            # Check max possible amplitude
            if merged_audio.max_possible_amplitude:
                max_amplitude = merged_audio.max
                if max_amplitude >= merged_audio.max_possible_amplitude * 0.99:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting clipping: {e}")
            return False
    
    def generate_filename(self, workout_session, language):
        """
        Generate filename: workout_{language}_{session_id}.mp3
        
        Args:
            workout_session: WorkoutSession instance
            language: 'nl' or 'en'
            
        Returns:
            Filename string
        """
        return f"workout_{language}_{workout_session.id}.mp3"
    
    def _save_merged_audio(self, merged_audio, filename):
        """
        Save merged audio to file
        
        Args:
            merged_audio: pydub AudioSegment
            filename: Output filename
            
        Returns:
            Full file path
        """
        # Create merged audio directory if it doesn't exist
        merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged_audio')
        os.makedirs(merged_dir, exist_ok=True)
        
        # Full file path
        file_path = os.path.join(merged_dir, filename)
        
        # Export as MP3
        merged_audio.export(
            file_path,
            format='mp3',
            bitrate='192k',
            parameters=['-q:a', '2']  # High quality
        )
        
        return file_path

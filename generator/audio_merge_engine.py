"""
Audio Merge Engine - Merges audio segments into single MP3
Handles scripts + quotes, applies normalization, prevents clipping
"""

import logging
import os
from pydub import AudioSegment as PydubSegment
from pydub.effects import normalize
from django.conf import settings

logger = logging.getLogger(__name__)


class AudioMergeEngine:
    """Merges audio segments into seamless MP3 file"""
    
    STANDARDIZED_PAUSE_MS = 2000
    TARGET_DBFS = -20.0
    MAX_DBFS = -1.0
    
    def merge_playlist(self, audio_playlist):
        """
        Merge all segments (scripts + quotes) into single MP3
        Returns: (success, file_path, error_message)
        """
        try:
            # Get available segments
            script_segments = audio_playlist.segments.filter(is_available=True).order_by('sequence_order')
            quote_segments = audio_playlist.quote_segments.filter(is_available=True).order_by('sequence_order')
            
            # Combine and sort by sequence
            all_segments = []
            for segment in script_segments:
                all_segments.append({'type': 'script', 'segment': segment, 'sequence': segment.sequence_order})
            for segment in quote_segments:
                all_segments.append({'type': 'quote', 'segment': segment, 'sequence': segment.sequence_order})
            
            all_segments.sort(key=lambda x: x['sequence'])
            
            if not all_segments:
                return (False, None, "No audio segments available")
            
            # Load audio files
            audio_files = []
            for item in all_segments:
                try:
                    audio_file = self._load_audio_file_from_segment(
                        item['segment'], item['type'], audio_playlist.language
                    )
                    if audio_file:
                        audio_files.append((item['segment'], audio_file))
                except Exception as e:
                    logger.error(f"Error loading {item['type']} segment {item['segment'].id}: {e}")
            
            if not audio_files:
                return (False, None, "Could not load any audio files")
            
            # Normalize, merge, check clipping
            normalized_files = self.normalize_volume(audio_files)
            merged_audio = self.insert_pauses_mixed(normalized_files)
            
            if self.detect_clipping(merged_audio):
                logger.warning(f"Clipping detected in playlist {audio_playlist.id}, reducing volume")
                merged_audio = merged_audio - 2  # Reduce by 2 dB
            
            # Save
            filename = self.generate_filename(audio_playlist.workout_session, audio_playlist.language)
            file_path = self._save_merged_audio(merged_audio, filename)
            
            # Delete old merged file if one already exists (re-merge scenario)
            if audio_playlist.merged_audio_file:
                try:
                    old_path = audio_playlist.merged_audio_file.path
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                        logger.info(f"Deleted old merged audio: {old_path}")
                except Exception as e:
                    logger.warning(f"Could not delete old merged file for playlist {audio_playlist.id}: {e}")

            # Update playlist — point the FileField at the already-saved file
            # (do NOT use .save() here; it would re-upload and create a duplicate with a random suffix)
            from django.utils import timezone
            audio_playlist.merged_audio_file = f'merged_audio/{filename}'
            audio_playlist.merged_at = timezone.now()
            audio_playlist.save()
            
            logger.info(f"Merged playlist {audio_playlist.id} to {file_path}")
            return (True, file_path, None)
            
        except Exception as e:
            logger.error(f"Error merging playlist {audio_playlist.id}: {e}", exc_info=True)
            return (False, None, f"Error: {str(e)}")
    
    def _load_audio_file_from_segment(self, segment, segment_type, language):
        """Load audio file from script or quote segment"""
        try:
            # Get audio file based on type
            if segment_type == 'script':
                audio_file = segment.session_script.workout_script.get_audio_file(language)
            else:  # quote
                audio_file = segment.session_quote.motivational_quote.get_audio_file(language)
            
            if not audio_file:
                logger.error(f"No audio for {segment_type} segment {segment.id} ({language})")
                return None
            
            # Get file path
            file_path = None
            try:
                if hasattr(audio_file, 'path'):
                    file_path = audio_file.path
            except Exception:
                pass
            
            if not file_path:
                file_path = os.path.join(settings.MEDIA_ROOT, audio_file.name)
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            # Load audio
            audio = PydubSegment.from_file(file_path)
            logger.info(f"Loaded {segment_type} audio: {len(audio)}ms from {file_path}")
            return audio
            
        except Exception as e:
            logger.error(f"Error loading {segment_type} segment {segment.id}: {e}", exc_info=True)
            return None
    
    def normalize_volume(self, audio_files):
        """Apply volume normalization, prevent clipping"""
        normalized = []
        
        for segment, audio in audio_files:
            try:
                normalized_audio = normalize(audio, headroom=1.0)
                
                # Ensure max dBFS not exceeded
                if normalized_audio.dBFS > self.MAX_DBFS:
                    reduction = normalized_audio.dBFS - self.MAX_DBFS
                    normalized_audio = normalized_audio - reduction
                
                normalized.append((segment, normalized_audio))
            except Exception as e:
                logger.error(f"Error normalizing segment {segment.id}: {e}")
                normalized.append((segment, audio))  # Use original
        
        return normalized
    
    def insert_pauses_mixed(self, audio_files):
        """Insert pauses between segments based on pause_after"""
        if not audio_files:
            return None
        
        merged = audio_files[0][1]
        
        for i in range(1, len(audio_files)):
            segment, audio = audio_files[i]
            previous_segment = audio_files[i-1][0]
            
            # Add pause if needed
            if previous_segment.pause_after > 0:
                pause_ms = int(previous_segment.pause_after * 1000)
                silence = PydubSegment.silent(duration=pause_ms)
                merged = merged + silence + audio
            else:
                merged = merged + audio
        
        return merged
    
    def detect_clipping(self, merged_audio):
        """Check if audio is clipping"""
        try:
            if merged_audio.dBFS > self.MAX_DBFS:
                return True
            
            if merged_audio.max_possible_amplitude:
                if merged_audio.max >= merged_audio.max_possible_amplitude * 0.99:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error detecting clipping: {e}")
            return False
    
    def generate_filename(self, workout_session, language):
        """Generate filename: workout_{language}_{session_id}.mp3"""
        return f"workout_{language}_{workout_session.id}.mp3"
    
    def _save_merged_audio(self, merged_audio, filename):
        """Save merged audio to file"""
        merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged_audio')
        os.makedirs(merged_dir, exist_ok=True)
        
        file_path = os.path.join(merged_dir, filename)
        
        merged_audio.export(file_path, format='mp3', bitrate='192k', parameters=['-q:a', '2'])
        
        return file_path

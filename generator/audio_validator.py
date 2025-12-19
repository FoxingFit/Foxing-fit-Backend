"""
Audio Validator Service

Validates audio files during upload and processing
- File format validation (MP3, WAV, M4A)
- Duration extraction and validation
- Audio integrity checking
"""

import logging
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.mp4 import MP4

logger = logging.getLogger(__name__)


class AudioValidator:
    """
    Validates audio files for workout script audio uploads
    """
    
    SUPPORTED_FORMATS = ['mp3', 'wav', 'm4a']
    DEFAULT_TOLERANCE = 0.20  # 20% tolerance for duration matching
    
    def validate_file_format(self, audio_file):
        """
        Validate file format is MP3, WAV, or M4A
        
        Args:
            audio_file: Django UploadedFile or file path
            
        Returns:
            (is_valid, format, error_message)
        """
        try:
            # Get file extension
            filename = getattr(audio_file, 'name', str(audio_file))
            extension = filename.lower().split('.')[-1]
            
            if extension not in self.SUPPORTED_FORMATS:
                return (False, None, f"Unsupported format: {extension}. Supported formats: {', '.join(self.SUPPORTED_FORMATS)}")
            
            return (True, extension, None)
            
        except Exception as e:
            logger.error(f"Error validating file format: {e}")
            return (False, None, f"Error validating file format: {str(e)}")
    
    def extract_duration(self, audio_file):
        """
        Extract audio duration in minutes using mutagen
        
        Args:
            audio_file: Django UploadedFile or file path
            
        Returns:
            (duration_minutes, error_message)
        """
        try:
            # Handle Django UploadedFile
            if hasattr(audio_file, 'temporary_file_path'):
                file_path = audio_file.temporary_file_path()
            elif hasattr(audio_file, 'path'):
                file_path = audio_file.path
            else:
                file_path = str(audio_file)
            
            # Use mutagen to extract duration
            audio = MutagenFile(file_path)
            
            if audio is None:
                return (None, "Could not read audio file")
            
            if not hasattr(audio.info, 'length'):
                return (None, "Audio file has no duration information")
            
            duration_seconds = audio.info.length
            duration_minutes = duration_seconds / 60.0
            
            return (round(duration_minutes, 1), None)
            
        except Exception as e:
            logger.error(f"Error extracting audio duration: {e}")
            return (None, f"Error extracting duration: {str(e)}")
    
    def validate_duration_match(self, audio_duration, text_duration, tolerance=None):
        """
        Validate audio duration is within tolerance of text duration
        
        Args:
            audio_duration: Duration of audio file in minutes
            text_duration: Duration of text script in minutes
            tolerance: Acceptable difference as decimal (default 0.20 = 20%)
            
        Returns:
            (is_valid, percentage_difference, error_message)
        """
        if tolerance is None:
            tolerance = self.DEFAULT_TOLERANCE
        
        if not audio_duration or not text_duration:
            return (False, None, "Missing duration values")
        
        try:
            difference = abs(audio_duration - text_duration)
            percentage_diff = (difference / text_duration) * 100
            
            is_valid = (difference / text_duration) <= tolerance
            
            if not is_valid:
                error_msg = f"Audio duration ({audio_duration:.1f}min) differs from text duration ({text_duration:.1f}min) by {percentage_diff:.1f}% (max {tolerance*100:.0f}%)"
                return (False, percentage_diff, error_msg)
            
            return (True, percentage_diff, None)
            
        except Exception as e:
            logger.error(f"Error validating duration match: {e}")
            return (False, None, f"Error validating duration: {str(e)}")
    
    def check_audio_integrity(self, audio_file):
        """
        Check if audio file is corrupted or invalid
        
        Args:
            audio_file: Django UploadedFile or file path
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # Handle Django UploadedFile
            if hasattr(audio_file, 'temporary_file_path'):
                file_path = audio_file.temporary_file_path()
            elif hasattr(audio_file, 'path'):
                file_path = audio_file.path
            else:
                file_path = str(audio_file)
            
            # Try to open and read basic info
            audio = MutagenFile(file_path)
            
            if audio is None:
                return (False, "Could not read audio file - file may be corrupted")
            
            # Check if we can access basic properties
            if not hasattr(audio.info, 'length'):
                return (False, "Audio file missing duration information")
            
            if audio.info.length <= 0:
                return (False, "Audio file has invalid duration")
            
            return (True, None)
            
        except Exception as e:
            logger.error(f"Error checking audio integrity: {e}")
            return (False, f"Audio file integrity check failed: {str(e)}")
    
    def validate_audio_upload(self, audio_file, text_duration, tolerance=None):
        """
        Complete validation for audio upload
        Combines format, integrity, and duration validation
        
        Args:
            audio_file: Django UploadedFile
            text_duration: Expected duration from text script in minutes
            tolerance: Duration tolerance (default 20%)
            
        Returns:
            (is_valid, audio_duration, errors_dict)
        """
        errors = {}
        
        # Validate format
        is_valid_format, format_type, format_error = self.validate_file_format(audio_file)
        if not is_valid_format:
            errors['format'] = format_error
            return (False, None, errors)
        
        # Check integrity
        is_valid_integrity, integrity_error = self.check_audio_integrity(audio_file)
        if not is_valid_integrity:
            errors['integrity'] = integrity_error
            return (False, None, errors)
        
        # Extract duration
        audio_duration, duration_error = self.extract_duration(audio_file)
        if duration_error:
            errors['duration_extraction'] = duration_error
            return (False, None, errors)
        
        # Validate duration match
        is_valid_duration, percentage_diff, duration_match_error = self.validate_duration_match(
            audio_duration, text_duration, tolerance
        )
        if not is_valid_duration:
            errors['duration_match'] = duration_match_error
            # Note: We still return the audio_duration even if validation fails
            # This allows admin to see the mismatch and decide
        
        is_valid = len(errors) == 0
        return (is_valid, audio_duration, errors)

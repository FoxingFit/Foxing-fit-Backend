from django.db import models
from scripts.models import WorkoutScript

class WorkoutSession(models.Model):
    """
    Generated workout sessions with sport-specific intelligence tracking
    
    Developer Notes:
    - Stores complete generated workouts with metadata
    - Tracks sport-specific additions for analytics
    - Provides time status analysis for Johnny's feedback
    - Links to individual scripts used via SessionScript model
    """
    
    # Core session information
    training_type = models.CharField(
        max_length=15, 
        choices=WorkoutScript.TRAINING_TYPES,
        help_text="Which sport this workout is for"
    )
    title = models.CharField(
        max_length=200,
        help_text="Generated workout name with date and goal"
    )
    total_duration = models.FloatField(
        help_text="Actual total time in minutes"
    )
    target_duration = models.FloatField(
        default=60.0,
        help_text="Target time you wanted (usually 60 minutes)"
    )
    time_flexibility = models.FloatField(
        default=5.0,
        help_text="How many minutes off-target is acceptable (±5 minutes)"
    )
    goal = models.CharField(
        max_length=15, 
        choices=WorkoutScript.GOALS,
        help_text="Fitness goal this workout targets"
    )
    
    # Generated content and intelligence metadata
    compiled_script = models.TextField(
        help_text="Complete workout script ready for voice recording"
    )
    
    # SPORT-SPECIFIC TRACKING - Developer: Stores what sport logic was applied
    sport_additions_applied = models.JSONField(
        default=dict,
        help_text="What sport-specific features were added automatically"
    )
    
    # Session tracking
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Johnny's usage tracking
    is_used = models.BooleanField(
        default=False,
        help_text="Check this after you record this workout"
    )
    notes = models.TextField(
        blank=True,
        help_text="Your notes about how this workout went"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Workout Session"
        verbose_name_plural = "Workout Sessions"
    
    def get_time_status(self):
        """
        Get human-readable time status with improved accuracy for custom durations
        Developer: Provides feedback on whether generation hit time targets
        """
        min_duration = self.target_duration - self.time_flexibility
        max_duration = self.target_duration + self.time_flexibility
        
        if self.total_duration < min_duration:
            off_by = min_duration - self.total_duration
            return f"Short ({self.total_duration:.1f}min, -{off_by:.1f}min from target)"
        elif self.total_duration > max_duration:
            off_by = self.total_duration - max_duration
            return f"Long ({self.total_duration:.1f}min, +{off_by:.1f}min over target)"
        else:
            return f"Perfect ({self.total_duration:.1f}min within ±{self.time_flexibility:.0f}min target)"
    
    def get_sport_logic_summary(self):
        """
        Get human-readable summary of sport logic applied
        Developer: Translates JSON metadata into readable format for Johnny
        """
        summary = []
        additions = self.sport_additions_applied
        
        if additions.get('surprise_rounds_added', 0) > 0:
            summary.append(f"{additions['surprise_rounds_added']} surprise rounds added")
        
        if additions.get('vinyasa_transitions_added', 0) > 0:
            summary.append(f"{additions['vinyasa_transitions_added']} vinyasa transitions added")
        
        if additions.get('max_challenge_moved_last', False):
            summary.append("MAX challenge placed at end")
        
        if additions.get('difficulty_reordered', False):
            summary.append("Difficulty progression applied")
        
        return "; ".join(summary) if summary else "Standard generation"
    
    def __str__(self):
        return f"{self.get_training_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class SessionScript(models.Model):
    """
    Individual scripts included in a generated workout session
    
    Developer Notes:
    - Links WorkoutSession to WorkoutScript with order and metadata
    - Tracks which scripts were added by sport-specific logic vs template
    - Enables analysis of generation patterns and script usage
    """
    
    workout_session = models.ForeignKey(
        WorkoutSession, 
        on_delete=models.CASCADE, 
        related_name='session_scripts',
        help_text="Which workout session this script belongs to"
    )
    workout_script = models.ForeignKey(
        WorkoutScript, 
        on_delete=models.CASCADE,
        help_text="The actual script that was used"
    )
    sequence_order = models.IntegerField(
        help_text="Order in the workout (1 = first, 2 = second, etc.)"
    )
    
    # SPORT-SPECIFIC TRACKING - Developer: Track what was added by sport logic
    is_sport_addition = models.BooleanField(
        default=False,
        help_text="Added by sport intelligence (surprise round, vinyasa, etc.)"
    )
    
    class Meta:
        ordering = ['sequence_order']
        verbose_name = "Session Script"
        verbose_name_plural = "Session Scripts"


class SessionQuote(models.Model):
    """
    Motivational quotes inserted between scripts in a workout session
    
    Developer Notes:
    - Tracks which quotes were used and where they were placed
    - Links to SessionScript to maintain insertion order
    - Enables audio playlist generation with quote audio
    """
    
    workout_session = models.ForeignKey(
        WorkoutSession,
        on_delete=models.CASCADE,
        related_name='session_quotes',
        help_text="Which workout session this quote belongs to"
    )
    motivational_quote = models.ForeignKey(
        'scripts.MotivationalQuote',
        on_delete=models.CASCADE,
        help_text="The motivational quote that was used"
    )
    inserted_after_script = models.ForeignKey(
        SessionScript,
        on_delete=models.CASCADE,
        related_name='quotes_after',
        help_text="The script this quote was inserted after"
    )
    sequence_order = models.IntegerField(
        help_text="Order in the workout (inserted between scripts)"
    )
    
    class Meta:
        ordering = ['sequence_order']
        verbose_name = "Session Quote"
        verbose_name_plural = "Session Quotes"
    
    def __str__(self):
        return f"Quote after {self.inserted_after_script.workout_script.title}: {self.motivational_quote.quote_text[:30]}..."


class AudioPlaylist(models.Model):
    """
    Audio playlist for a workout session
    
    Developer Notes:
    - Represents a complete audio workout in a specific language
    - Tracks completeness and duration including pauses
    - Links to individual audio segments in sequence
    """
    
    LANGUAGES = [
        ('nl', 'Dutch'),
        ('en', 'English'),
    ]
    
    workout_session = models.ForeignKey(
        WorkoutSession,
        on_delete=models.CASCADE,
        related_name='audio_playlists',
        help_text="Which workout session this audio playlist belongs to"
    )
    language = models.CharField(
        max_length=2,
        choices=LANGUAGES,
        help_text="Language of this audio playlist"
    )
    total_duration = models.FloatField(
        help_text="Total duration including pauses in minutes"
    )
    segment_count = models.IntegerField(
        help_text="Total number of segments in playlist"
    )
    available_segment_count = models.IntegerField(
        help_text="Number of segments with available audio"
    )
    merged_audio_file = models.FileField(
        upload_to='merged_audio/',
        null=True,
        blank=True,
        help_text="Merged audio file (all segments combined)"
    )
    merged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the audio was last merged"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['workout_session', 'language']
        ordering = ['-created_at']
        verbose_name = "Audio Playlist"
        verbose_name_plural = "Audio Playlists"
    
    def get_completeness_percentage(self):
        """Calculate percentage of segments with audio"""
        if self.segment_count == 0:
            return 0.0
        return (self.available_segment_count / self.segment_count) * 100
    
    def is_complete(self):
        """Check if all segments have audio"""
        return self.segment_count == self.available_segment_count
    
    def __str__(self):
        completeness = self.get_completeness_percentage()
        return "{} - {} ({:.0f}% complete)".format(
            str(self.workout_session), 
            self.get_language_display(), 
            completeness
        )


class AudioSegment(models.Model):
    """
    Individual audio segment within a playlist
    
    Developer Notes:
    - Links to SessionScript to maintain workout structure
    - Tracks audio availability and duration
    - Includes pause duration after segment
    """
    
    audio_playlist = models.ForeignKey(
        AudioPlaylist,
        on_delete=models.CASCADE,
        related_name='segments',
        help_text="Which audio playlist this segment belongs to"
    )
    session_script = models.ForeignKey(
        SessionScript,
        on_delete=models.CASCADE,
        help_text="The workout script this audio represents"
    )
    sequence_order = models.IntegerField(
        help_text="Order in the playlist (matches SessionScript order)"
    )
    audio_file = models.FileField(
        upload_to='merged_audio/',
        null=True,
        blank=True,
        help_text="Reference to the audio file"
    )
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Duration of this audio segment in minutes"
    )
    is_available = models.BooleanField(
        default=False,
        help_text="Whether audio is available for this segment"
    )
    pause_after = models.FloatField(
        default=2.0,
        help_text="Pause duration after this segment in seconds"
    )
    
    class Meta:
        ordering = ['sequence_order']
        unique_together = ['audio_playlist', 'sequence_order']
        verbose_name = "Audio Segment"
        verbose_name_plural = "Audio Segments"
    
    def __str__(self):
        status = "Available" if self.is_available else "Missing"
        return f"Segment {self.sequence_order}: {self.session_script.workout_script.title} ({status})"


class AudioQuoteSegment(models.Model):
    """
    Motivational quote audio segments within a playlist
    
    Developer Notes:
    - Links to SessionQuote to maintain quote placement
    - Tracks audio availability and duration for quotes
    - Inserted between script segments just like text quotes
    """
    
    audio_playlist = models.ForeignKey(
        AudioPlaylist,
        on_delete=models.CASCADE,
        related_name='quote_segments',
        help_text="Which audio playlist this quote segment belongs to"
    )
    session_quote = models.ForeignKey(
        SessionQuote,
        on_delete=models.CASCADE,
        help_text="The session quote this audio represents"
    )
    sequence_order = models.IntegerField(
        help_text="Order in the playlist (inserted between script segments)"
    )
    audio_file = models.FileField(
        upload_to='merged_audio/',
        null=True,
        blank=True,
        help_text="Reference to the quote audio file"
    )
    duration = models.FloatField(
        null=True,
        blank=True,
        help_text="Duration of this quote audio in minutes"
    )
    is_available = models.BooleanField(
        default=False,
        help_text="Whether audio is available for this quote"
    )
    pause_after = models.FloatField(
        default=2.0,
        help_text="Pause duration after this quote in seconds"
    )
    
    class Meta:
        ordering = ['sequence_order']
        verbose_name = "Audio Quote Segment"
        verbose_name_plural = "Audio Quote Segments"
    
    def __str__(self):
        status = "Available" if self.is_available else "Missing"
        quote_preview = self.session_quote.motivational_quote.quote_text[:30]
        return f"Quote Segment {self.sequence_order}: {quote_preview}... ({status})"

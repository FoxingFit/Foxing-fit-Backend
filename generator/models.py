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

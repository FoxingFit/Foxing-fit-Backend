from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import re

class ScriptCategory(models.Model):
    """
    SYSTEM CATEGORIES APPROACH - Fixed special categories that cannot be deleted
    """
    TRAINING_TYPES = [
        ('kickboxing', 'Kickboxing Heavybag'),
        ('power_yoga', 'Power Yoga'),
        ('calisthenics', 'Calisthenics'),
    ]
    
    # FIXED SYSTEM CATEGORIES - These exact names are protected and enable sport logic
    SYSTEM_CATEGORIES = {
        # Kickboxing system categories
        'kb_surprise': {
            'training_type': 'kickboxing',
            'default_display_name': 'Surprise Rounds',
            'description': 'System category for automatic surprise round insertion',
        },
        
        # Calisthenics system categories  
        'cal_max_challenge': {
            'training_type': 'calisthenics',
            'default_display_name': 'MAX Challenge',
            'description': 'System category for MAX challenge rounds placed at workout end',
        },
        
        # Power Yoga system categories
        'py_vinyasa_s2s': {
            'training_type': 'power_yoga',
            'default_display_name': 'Vinyasa Standing-to-Standing',
            'description': 'System category for standing-to-standing flow transitions',
        },
        
        'py_vinyasa_s2sit': {
            'training_type': 'power_yoga',
            'default_display_name': 'Vinyasa Standing-to-Sitting',
            'description': 'System category for standing-to-sitting flow transitions',
        },
    }
    
    # Core fields
    name = models.CharField(
        max_length=50, 
        help_text="System name - PROTECTED for system categories"
    )
    display_name = models.CharField(
        max_length=100, 
        help_text="Display name - can be customized even for system categories"
    )
    training_type = models.CharField(max_length=15, choices=TRAINING_TYPES)
    description = models.TextField(blank=True, help_text="What this section is for")
    
    # System category flag
    is_system_category = models.BooleanField(
        default=False,
        help_text="System category - cannot be deleted, name cannot be changed"
    )
    
    # Management
    is_active = models.BooleanField(default=True, help_text="Turn off to hide this category")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['name', 'training_type']
        ordering = ['training_type', 'display_name']
        verbose_name = "Script Category"
        verbose_name_plural = "Script Categories"
    
    def clean(self):
        """Validate system category constraints"""
        super().clean()
        
        # If this is a system category, validate it matches expected structure
        if self.name and self.name in self.SYSTEM_CATEGORIES:
            expected = self.SYSTEM_CATEGORIES[self.name]
            
            # Force correct training type for system categories
            if self.training_type != expected['training_type']:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"System category '{self.name}' must have training_type '{expected['training_type']}'"
                )
            
            # Auto-set system flag
            self.is_system_category = True
    
    def save(self, *args, **kwargs):
        # Auto-detect and protect system categories
        if self.name and self.name in self.SYSTEM_CATEGORIES:
            self.is_system_category = True
            
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of system categories"""
        if self.is_system_category:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Cannot delete system category '{self.name}'. This category is required for sport-specific logic.")
        return super().delete(*args, **kwargs)
    
    # SIMPLE, EXACT DETECTION METHODS - No complex logic needed!
    def is_surprise_round(self):
        """Exact name matching - no complex detection needed"""
        return self.name == 'kb_surprise'
    
    def is_max_challenge(self):
        """Exact name matching - no complex detection needed"""
        return self.name == 'cal_max_challenge'
    
    def is_vinyasa_standing_to_standing(self):
        """Exact name matching - no complex detection needed"""
        return self.name == 'py_vinyasa_s2s'
    
    def is_vinyasa_standing_to_sitting(self):
        """Exact name matching - no complex detection needed"""
        return self.name == 'py_vinyasa_s2sit'
    
    def is_vinyasa_transition(self):
        """Check if this is any vinyasa transition"""
        return self.name in ['py_vinyasa_s2s', 'py_vinyasa_s2sit']
    
    def is_system_special_category(self):
        """Check if this is any system special category"""
        return self.name in self.SYSTEM_CATEGORIES
    
    @classmethod
    def create_system_categories(cls):
        """
        Create all required system categories
        Called during system setup to ensure special categories exist
        """
        created_categories = []
        
        for name, config in cls.SYSTEM_CATEGORIES.items():
            category, created = cls.objects.get_or_create(
                name=name,
                training_type=config['training_type'],
                defaults={
                    'display_name': config['default_display_name'],
                    'description': config['description'],
                    'is_system_category': True,
                    'is_active': True
                }
            )
            
            if created:
                created_categories.append(category)
        
        return created_categories
    
    @classmethod
    def get_system_category(cls, name):
        """
        Get a system category by exact name
        Returns None if not found or not a system category
        """
        try:
            category = cls.objects.get(name=name, is_system_category=True)
            return category
        except cls.DoesNotExist:
            return None
    
    def __str__(self):
        system_indicator = " (SYSTEM)" if self.is_system_category else ""
        return f"{self.get_training_type_display()} - {self.display_name}{system_indicator}"

class WorkoutScript(models.Model):
    
    TRAINING_TYPES = ScriptCategory.TRAINING_TYPES
    
    GOALS = [
        ('allround', 'All-round'),
        ('strength', 'Strength'),
        ('flexibility', 'Flexibility'),
    ]
    
    LANGUAGES = [
        ('nl', 'Dutch'),
        ('en', 'English'),
    ]
    
    # Core fields
    title = models.CharField(
        max_length=200,
        help_text="Name for this script - 'Round 1:' will be removed automatically"
    )
    type = models.CharField(
        max_length=15, 
        choices=TRAINING_TYPES, 
        db_index=True,
        help_text="Which sport this script is for"
    )
    script_category = models.ForeignKey(
        ScriptCategory, 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text="What type of exercise this is (warmup, combos, surprise, etc.)"
    )
    goal = models.CharField(
        max_length=15, 
        choices=GOALS, 
        db_index=True,
        help_text="What fitness goal this targets"
    )
    content = models.TextField(
        help_text="The actual script text with [pause strong]/[pause weak] markers"
    )
    duration_minutes = models.FloatField(
        help_text="How long this takes to speak in minutes"
    )
    language = models.CharField(
        max_length=2, 
        choices=LANGUAGES, 
        default='nl',
        help_text="Language for this script"
    )
    
    # Usage tracking for variety
    times_selected = models.IntegerField(
        default=0,
        help_text="How often this was used - system tracks automatically"
    )
    last_selected = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this was last used - system tracks automatically"
    )
    
    # Management
    is_active = models.BooleanField(
        default=True,
        help_text="Turn off to hide this script without deleting it"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(
        blank=True, 
        help_text="Your personal notes about this script"
    )
    
    class Meta:
        ordering = ['type', 'script_category__display_name', 'title']
        indexes = [
            models.Index(fields=['type', 'script_category', 'goal']),
            models.Index(fields=['times_selected', 'last_selected']),
        ]
        verbose_name = "Workout Script"
        verbose_name_plural = "Workout Scripts"
    
    def clean_title(self):
        """Remove round numbers from title"""
        self.title = re.sub(r'^(Round|Ronde)\s+\d+:\s*', '', self.title, flags=re.IGNORECASE).strip()
    
    def save(self, *args, **kwargs):
        self.clean_title()
        # AUTO-ROUND duration to 1 decimal place
        if self.duration_minutes is not None:
            self.duration_minutes = round(self.duration_minutes, 1)
        super().save(*args, **kwargs)
    
    def mark_selected(self):
        """Track selection for variety algorithm"""
        self.times_selected += 1
        self.last_selected = timezone.now()
        self.save(update_fields=['times_selected', 'last_selected'])
    
    def get_freshness_score(self):
        """
        Calculate freshness score for variety algorithm
        Returns 0.3-1.0 score, higher = fresher (less recently used)
        """
        if not self.last_selected:
            return 1.0  # Never used = most fresh
        
        days_since = (timezone.now() - self.last_selected).days
        if days_since >= 14:
            return 1.0      # Very fresh
        elif days_since >= 7:
            return 0.8      # Fresh
        elif days_since >= 3:
            return 0.6      # Somewhat fresh
        else:
            return 0.3      # Recently used = less fresh
    
    # Special round detection using category names
    def is_surprise_round(self):
        return self.script_category.is_surprise_round()
    
    def is_max_challenge(self):
        return self.script_category.is_max_challenge()
    
    def is_vinyasa_transition(self):
        return self.script_category.is_vinyasa_transition()
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.title}"

class MotivationalQuote(models.Model):
    """
    Johnny's "Onthoud..." motivational quotes system
    
    Developer Notes:
    - These are the green text motivational insertions
    - Auto-formatted with "Onthoud, [quote_text]" pattern
    - Usage tracking prevents repetition within sessions
    """
    
    TRAINING_TYPES = WorkoutScript.TRAINING_TYPES
    
    # Core quote fields
    training_type = models.CharField(
        max_length=15, 
        choices=TRAINING_TYPES,
        help_text="Which sport this motivational quote is for"
    )
    quote_text = models.TextField(
        help_text="The motivational text - 'Onthoud,' will be added automatically"
    )
   
    target_category = models.ForeignKey(
        'ScriptCategory',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='specific_quotes',
        help_text="Specific exercise category (leave blank for general quotes)"
    )
    is_exercise_specific = models.BooleanField(
        default=False,
        help_text="Only use during the selected exercise category"
    )


    language = models.CharField(
        max_length=2, 
        choices=WorkoutScript.LANGUAGES, 
        default='nl',
        help_text="Language for this quote"
    )
    
    # USAGE TRACKING - Prevents quote repetition and ensures variety
    times_used = models.IntegerField(
        default=0,
        help_text="How often this quote was used - system tracks automatically"
    )
    last_used = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When this quote was last used - system tracks automatically"
    )
    
    # Management
    is_active = models.BooleanField(
        default=True,
        help_text="Turn off to hide this quote without deleting it"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['training_type', 'is_exercise_specific', 'target_category']
        verbose_name = "Motivational Quote"
        verbose_name_plural = "Motivational Quotes"

    def clean(self):
        """Validation to ensure consistency"""
        from django.core.exceptions import ValidationError
        
        if self.is_exercise_specific and not self.target_category:
            raise ValidationError("Exercise-specific quotes must have a target category")
        if not self.is_exercise_specific and self.target_category:
            raise ValidationError("General quotes should not have a target category")
        
        # Ensure target_category matches training_type
        if self.target_category and self.target_category.training_type != self.training_type:
            raise ValidationError("Target category must match the quote's training type")
        
    def save(self, *args, **kwargs):
        """Auto-set is_exercise_specific based on target_category"""
        self.is_exercise_specific = bool(self.target_category)
        super().save(*args, **kwargs)
    
    # USAGE TRACKING METHODS - Power the quote variety system
    def mark_used(self):
        """Track usage for variety in quote selection"""
        self.times_used += 1
        self.last_used = timezone.now()
        self.save(update_fields=['times_used', 'last_used'])
    
    def get_formatted_quote(self):
        """Returns the quote in Johnny's standard format"""
        return f"Onthoud, [{self.quote_text}]"
    
    def matches_script_category(self, script_category):
        """Check if this quote matches the given script category"""
        if not self.is_exercise_specific:
            return True  # General quotes match any category
        return self.target_category_id == script_category.id
    
    def __str__(self):
        category_info = f" ({self.target_category.display_name})" if self.target_category else " (General)"
        return f"{self.get_training_type_display()}{category_info} - {self.quote_text[:50]}..."


class WorkoutTemplate(models.Model):
    """
    Johnny's flexible workout structure rules with sport-specific logic
    - Defines the order and rules for workout generation
    - Supports OR logic through alternative_categories
    - Contains sport-specific automation rules for surprise rounds, vinyasa, etc.
    """
    
    VINYASA_TYPES = [
        ('standing_to_standing', 'Standing to Standing'),
        ('standing_to_sitting', 'Standing to Sitting'),
    ]
    
    # Core template structure
    training_type = models.CharField(
        max_length=15, 
        choices=ScriptCategory.TRAINING_TYPES,
        help_text="Which sport this template is for"
    )
    sequence_order = models.IntegerField(
        help_text="Order in workout (1 = first, 2 = second, etc.) - higher numbers come later"
    )
    primary_category = models.ForeignKey(
        ScriptCategory, 
        on_delete=models.CASCADE, 
        related_name='primary_templates',
        help_text="Main type of exercise for this step"
    )
    
    # OR LOGIC SUPPORT
    alternative_categories = models.ManyToManyField(
        ScriptCategory, 
        blank=True, 
        related_name='alternative_templates',
        help_text="Other exercise types that can be used instead (creates 'A OR B OR C' choice)"
    )
    
    # Basic rules
    is_required = models.BooleanField(
        default=True,
        help_text="Must be included in every workout (when this template step is active)"
    )
    
    # NEW: Active/Inactive control for template steps
    is_active = models.BooleanField(
        default=True,
        help_text="Turn off to disable this template step without deleting it"
    )
    
    # METHOD 1: Checkbox approach - system auto-selects categories
    add_surprise_round_after = models.BooleanField(
        default=False,
        help_text="Add a surprise round after this step (system will auto-find surprise category)"
    )
    
    add_max_challenge_after = models.BooleanField(
        default=False,
        help_text="Add a MAX challenge after this step (system will auto-find MAX challenge category)"
    )
    
    add_vinyasa_transition_after = models.BooleanField(
        default=False,
        help_text="Add a vinyasa transition after this step (system will auto-find vinyasa category)"
    )
    
    vinyasa_type = models.CharField(
        max_length=25,
        choices=VINYASA_TYPES,
        blank=True,
        null=True,
        help_text="Which type of vinyasa transition (system will auto-find matching category)"
    )
    
    # OPTIONAL: Time constraints
    min_duration = models.FloatField(
        null=True, 
        blank=True,
        help_text="Minimum time for this section in minutes (optional)"
    )
    max_duration = models.FloatField(
        null=True, 
        blank=True,
        help_text="Maximum time for this section in minutes (optional)"
    )
    preferred_duration = models.FloatField(
        null=True, 
        blank=True,
        help_text="Ideal time for this section in minutes (optional)"
    )
    
    # Management tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['training_type', 'sequence_order']
        ordering = ['training_type', 'sequence_order']
        verbose_name = "Workout Template"
        verbose_name_plural = "Workout Templates"
    
    def get_all_possible_categories(self):
        """Get primary category + all alternatives for OR logic"""
        categories = [self.primary_category]
        categories.extend(self.alternative_categories.all())
        return categories
    
    def get_special_round_category_to_add_after(self):
        """
        AUTO-SELECT special round category based on checkbox settings (Method 1)
        System automatically finds the right category - admin doesn't need to select
        """
        if self.add_surprise_round_after:
            # System auto-finds surprise round category for this sport
            surprise_category = ScriptCategory.objects.filter(
                training_type=self.training_type,
                name__icontains='surprise',  # Auto-find by name pattern
                is_active=True
            ).first()
            return surprise_category
        
        elif self.add_max_challenge_after:
            # System auto-finds MAX challenge category for this sport
            max_category = ScriptCategory.objects.filter(
                training_type=self.training_type,
                name__icontains='max',  # Auto-find by name pattern
                is_active=True
            ).first()
            return max_category
        
        elif self.add_vinyasa_transition_after and self.vinyasa_type:
            if self.vinyasa_type == 'standing_to_sitting':
                vinyasa_category = ScriptCategory.objects.filter(
                    training_type=self.training_type,
                    name='py_vinyasa_s2sit',  #EXACT match
                    is_active=True
                ).first()
            elif self.vinyasa_type == 'standing_to_standing':
                vinyasa_category = ScriptCategory.objects.filter(
                    training_type=self.training_type,
                    name='py_vinyasa_s2s',   #EXACT match
                    is_active=True
                ).first()
            else:
                vinyasa_category = None
            
            return vinyasa_category
        
        return None
    
    def should_add_special_round(self):
        """Alias for get_special_round_category_to_add_after() for generator compatibility"""
        return self.get_special_round_category_to_add_after()
    
    def has_any_special_addition(self):
        """Check if this template step adds any special round after"""
        return (self.add_surprise_round_after or 
                self.add_max_challenge_after or 
                self.add_vinyasa_transition_after)
    
    def __str__(self):
        alternatives = list(self.alternative_categories.values_list('display_name', flat=True))
        alt_text = f" OR {', '.join(alternatives)}" if alternatives else ""
        
        special_additions = []
        if self.add_surprise_round_after:
            special_additions.append("+ Auto-Surprise")
        if self.add_max_challenge_after:
            special_additions.append("+ Auto-MAX")
        if self.add_vinyasa_transition_after:
            vinyasa_display = f"Auto-Vinyasa ({self.vinyasa_type})" if self.vinyasa_type else "Auto-Vinyasa"
            special_additions.append(f"+ {vinyasa_display}")
        
        special_text = f" {' '.join(special_additions)}" if special_additions else ""
        
        active_status = "" if self.is_active else " [INACTIVE]"
        
        return f"{self.get_training_type_display()} - Step {self.sequence_order}: {self.primary_category.display_name}{alt_text}{special_text}{active_status}"
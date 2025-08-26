from django.contrib import admin
from .models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory
from django.utils.html import format_html
from django.core.exceptions import ValidationError

@admin.register(ScriptCategory)
class ScriptCategoryAdmin(admin.ModelAdmin):
    # FIXED: Remove system_category_indicator, combine into special_round_indicator
    list_display = ['display_name', 'training_type', 'special_round_indicator', 'is_active']
    list_filter = ['training_type', 'is_system_category', 'is_active']
    search_fields = ['display_name', 'name', 'description']
    readonly_fields = ['is_system_category', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('display_name', 'training_type', 'name', 'description'),
            'description': 'Category details. System categories have protected names.'
        }),
        ('System Information', {
            'fields': ('is_system_category', 'created_at'),
            'classes': ('collapse',),
            'description': 'System-managed fields.'
        }),
        ('Management', {
            'fields': ('is_active',),
            'description': 'Turn off to hide this category from the system.'
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make name and training_type readonly for system categories"""
        readonly = list(self.readonly_fields)
        
        if obj and obj.is_system_category:
            readonly.append('name')
            readonly.append('training_type')
            
        return readonly
    
    def special_round_indicator(self, obj):
        """FIXED: Combined indicator showing both system status and special function"""
        if obj.is_system_category:
            # Show system lock + special function
            if obj.is_surprise_round():
                return format_html('<span style="color: #FF9800; font-weight: bold;">🔒 🎯 Surprise Round</span>')
            elif obj.is_max_challenge():
                return format_html('<span style="color: #E91E63; font-weight: bold;">🔒 💪 MAX Challenge</span>')
            elif obj.is_vinyasa_standing_to_standing():
                return format_html('<span style="color: #009688; font-weight: bold;">🔒 🌊 Vinyasa S→S</span>')
            elif obj.is_vinyasa_standing_to_sitting():
                return format_html('<span style="color: #009688; font-weight: bold;">🔒 🌊 Vinyasa S→Sit</span>')
            else:
                return format_html('<span style="color: #2196F3; font-weight: bold;">🔒 SYSTEM</span>')
        else:
            # Regular categories
            if obj.is_surprise_round():
                return "🎯 Surprise Round"
            elif obj.is_max_challenge():
                return "💪 MAX Challenge"
            elif obj.is_vinyasa_standing_to_standing():
                return "🌊 Vinyasa S→S"
            elif obj.is_vinyasa_standing_to_sitting():
                return "🌊 Vinyasa S→Sit"
            else:
                return "📝 Regular Exercise"
    special_round_indicator.short_description = 'Type'
    
    def delete_model(self, request, obj):
        """Prevent deletion of system categories"""
        if obj.is_system_category:
            from django.contrib import messages
            messages.error(request, f"Cannot delete system category '{obj.name}'. This category is required for sport-specific automation.")
            return  # Don't delete, just return
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Prevent bulk deletion of system categories"""
        system_categories = queryset.filter(is_system_category=True)
        if system_categories.exists():
            system_names = list(system_categories.values_list('name', flat=True))
            from django.contrib import messages
            messages.error(request, f"Cannot delete system categories: {', '.join(system_names)}. These are required for sport automation.")
            # Delete only non-system categories
            non_system_categories = queryset.filter(is_system_category=False)
            if non_system_categories.exists():
                super().delete_queryset(request, non_system_categories)
            return
        super().delete_queryset(request, queryset)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if obj and obj.is_system_category:
            if 'name' in form.base_fields:
                form.base_fields['name'].help_text = "🔒 SYSTEM CATEGORY - Name cannot be changed (required for automation)"
            if 'display_name' in form.base_fields:
                form.base_fields['display_name'].help_text = "✏️ You can customize this display name"
            if 'training_type' in form.base_fields:
                form.base_fields['training_type'].help_text = "🔒 Protected for system category"

        return form
    
    def has_delete_permission(self, request, obj=None):
        """Allow showing delete button, but handle protection in delete_model"""
        return True

@admin.register(WorkoutScript)
class WorkoutScriptAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'script_category', 'special_round_indicator', 'goal', 'duration_display', 'freshness_indicator', 'is_active']
    list_filter = ['type', 'script_category__training_type', 'goal', 'is_active']
    search_fields = ['title', 'content']
    readonly_fields = ['times_selected', 'last_selected', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'type', 'script_category', 'goal', 'language'),
            'description': 'Essential details about this workout script.'
        }),
        ('Content & Timing', {
            'fields': ('content', 'duration_minutes'),
            'description': 'The actual script text and speaking duration.'
        }),
        ('Management', {
            'fields': ('is_active', 'notes'),
            'description': 'Control and notes for this script.'
        }),
        ('Usage Statistics', {
            'fields': ('times_selected', 'last_selected'),
            'classes': ('collapse',),
            'description': 'Automatically tracked for variety.'
        }),
    )

    def duration_display(self, obj):
        """Show duration in MM:SS format"""
        return obj.get_duration_display() 
    duration_display.short_description = 'Duration'
    
    # Override form field help text
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'duration_minutes' in form.base_fields:
            form.base_fields['duration_minutes'].help_text = "💡 Enter as 3:30 (3min 30sec) or 3.5 (decimal) - both work!"
        return form
    
    def special_round_indicator(self, obj):
        """Show if this is a special round script"""
        if obj.is_surprise_round():
            return "🎯"
        elif obj.is_max_challenge():
            return "💪"
        elif obj.is_vinyasa_transition():
            return "🌊"
        else:
            return "📝"
    special_round_indicator.short_description = 'Type'
    
    def freshness_indicator(self, obj):
        """Show how fresh this script is"""
        score = obj.get_freshness_score()
        if score >= 0.8:
            return f"🟢 Fresh ({score:.1f})"
        elif score >= 0.6:
            return f"🟡 Used ({score:.1f})"
        else:
            return f"🔴 Overused ({score:.1f})"
    freshness_indicator.short_description = 'Freshness'

@admin.register(WorkoutTemplate)
class WorkoutTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'sequence_order',
        'training_type', 
        'primary_category', 
        'alternatives_preview', 
        'auto_additions_preview',
        'is_required',
        'active_status',
        'placement_warnings'
    ]
    list_filter = [
        'training_type', 
        'add_surprise_round_after', 
        'add_max_challenge_after', 
        'add_vinyasa_transition_after',
        'is_required',
        'is_active'
    ]
    ordering = ['training_type', 'sequence_order']
    
    filter_horizontal = ['alternative_categories']
    
    fieldsets = (
        ('Template Structure', {
            'fields': (
                'training_type', 
                'sequence_order', 
                'primary_category', 
                'alternative_categories', 
                'is_required'
            ),
            'description': 'Basic workout step configuration. Use sequence_order to control when things appear (1=first, 2=second, etc.).'
        }),
        ('🎯 Auto-Add Surprise Round After? (Kickboxing)', {
            'fields': ('add_surprise_round_after',),
            'description': 'Check to automatically add a surprise round after this step. System will find the surprise category automatically. <br><strong>⚠️ Warning: Avoid placing surprise rounds after warmup, cooldown, or stretch sections.</strong>',
            'classes': ('collapse',),
        }),
        ('💪 Auto-Add MAX Challenge After? (Calisthenics)', {
            'fields': ('add_max_challenge_after',),
            'description': 'Check to automatically add a MAX challenge after this step. System will find the MAX challenge category automatically. <br><strong>⚠️ Warning: MAX challenges work best near the end of workouts after proper warmup and preparation.</strong>',
            'classes': ('collapse',),
        }),
        ('🌊 Auto-Add Vinyasa Transition After? (Power Yoga)', {
            'fields': ('add_vinyasa_transition_after', 'vinyasa_type'),
            'description': 'Check to automatically add a vinyasa transition and select which type. System will find the matching vinyasa category automatically. <br><strong>⚠️ Warning: Vinyasa transitions work best between pose changes, not after warmup or before final relaxation.</strong>',
            'classes': ('collapse',),
        }),
        ('Management', {
            'fields': ('is_active',),
            'description': 'Turn off to disable this template step without deleting it.'
        }),
        ('Advanced (Optional)', {
            'fields': ('min_duration', 'max_duration', 'preferred_duration'),
            'classes': ('collapse',),
            'description': 'Optional time constraints for this section.'
        }),
    )
    
    def alternatives_preview(self, obj):
        """Show alternative categories"""
        alternatives = obj.alternative_categories.all()[:2]
        alt_names = [alt.display_name for alt in alternatives]
        preview = ", ".join(alt_names)
        if obj.alternative_categories.count() > 2:
            preview += f" (+{obj.alternative_categories.count() - 2} more)"
        return preview or "None"
    alternatives_preview.short_description = 'OR Options'
    
    def auto_additions_preview(self, obj):
        """Show what will be automatically added"""
        additions = []
        if obj.add_surprise_round_after:
            additions.append("🎯 Auto-Surprise")
        if obj.add_max_challenge_after:
            additions.append("💪 Auto-MAX")
        if obj.add_vinyasa_transition_after:
            if obj.vinyasa_type:
                if obj.vinyasa_type == 'standing_to_standing':
                    additions.append("🌊 Auto-S→S")
                elif obj.vinyasa_type == 'standing_to_sitting':
                    additions.append("🌊 Auto-S→Sit")
                else:
                    additions.append("🌊 Auto-Vinyasa")
            else:
                additions.append("🌊 Auto-Vinyasa (No type selected)")
        
        return " ".join(additions) if additions else "None"
    auto_additions_preview.short_description = 'Auto-Added After'
    
    def active_status(self, obj):
        """Show active/inactive status with visual indicator"""
        if obj.is_active:
            return "✅ Active"
        else:
            return "❌ Inactive"
    active_status.short_description = 'Status'
    
    def placement_warnings(self, obj):
        """Show intelligent warnings about potentially inappropriate placements"""
        warnings = []
        
        if obj.primary_category:
            category_name = obj.primary_category.name.lower()
            
            # Check for surprise round warnings
            if obj.add_surprise_round_after:
                if any(term in category_name for term in ['warmup', 'warm-up', 'cooldown', 'cool-down', 'stretch', 'relax']):
                    warnings.append("⚠️ Surprise after gentle section")
                if obj.sequence_order <= 1:
                    warnings.append("⚠️ Surprise too early")
            
            # Check for MAX challenge warnings  
            if obj.add_max_challenge_after:
                if any(term in category_name for term in ['warmup', 'warm-up']):
                    warnings.append("⚠️ MAX after warmup")
                if obj.sequence_order <= 2:
                    warnings.append("⚠️ MAX challenge too early")
            
            # Check for vinyasa warnings
            if obj.add_vinyasa_transition_after:
                if any(term in category_name for term in ['warmup', 'warm-up', 'savasana', 'mindfulness']):
                    warnings.append("⚠️ Vinyasa after gentle section")
                if 'connecting' in category_name:
                    warnings.append("⚠️ Vinyasa after connecting phase")
        
        return " | ".join(warnings) if warnings else "✅ Good placement"
    placement_warnings.short_description = 'Placement Analysis'
    
    def save_model(self, request, obj, form, change):
        """Override save to show warnings in admin messages"""
        # Save the object first
        super().save_model(request, obj, form, change)
        
        # Generate placement warnings and show as admin messages
        warnings = self._generate_detailed_warnings(obj)
        
        if warnings:
            from django.contrib import messages
            for warning in warnings:
                messages.warning(request, warning)
        else:
            from django.contrib import messages
            messages.success(request, f"Template step {obj.sequence_order} configured successfully with optimal placement.")
    
    def _generate_detailed_warnings(self, obj):
        """Generate detailed warnings about special round placement"""
        warnings = []
        
        if not obj.primary_category:
            return warnings
            
        category_name = obj.primary_category.name.lower()
        category_display = obj.primary_category.display_name
        
        # Surprise round warnings
        if obj.add_surprise_round_after:
            if any(term in category_name for term in ['warmup', 'warm-up']):
                warnings.append(f"⚠️ Surprise Round Warning: Adding surprise rounds after '{category_display}' (warmup) may be too intense. Consider placing surprise rounds after main exercise sections instead.")
            
            elif any(term in category_name for term in ['cooldown', 'cool-down', 'stretch', 'relax', 'savasana']):
                warnings.append(f"⚠️ Surprise Round Warning: Adding surprise rounds after '{category_display}' (cooldown/stretch) disrupts the relaxation flow. Surprise rounds work best after intense exercise sections.")
            
            elif obj.sequence_order <= 1:
                warnings.append(f"⚠️ Surprise Round Warning: Sequence order {obj.sequence_order} may be too early for surprise rounds. Consider placing them after participants are warmed up.")
        
        # MAX challenge warnings
        if obj.add_max_challenge_after:
            if any(term in category_name for term in ['warmup', 'warm-up']):
                warnings.append(f"⚠️ MAX Challenge Warning: Adding MAX challenges after '{category_display}' (warmup) may risk injury. MAX challenges should come after proper preparation and main exercises.")
            
            elif obj.sequence_order <= 2:
                warnings.append(f"⚠️ MAX Challenge Warning: Sequence order {obj.sequence_order} may be too early for MAX challenges. They typically work best near the end after adequate preparation.")
        
        # Vinyasa warnings
        if obj.add_vinyasa_transition_after:
            if any(term in category_name for term in ['warmup', 'warm-up', 'connecting']):
                warnings.append(f"⚠️ Vinyasa Warning: Adding vinyasa transitions after '{category_display}' (opening phase) may be premature. Vinyasa flows work best between established poses.")
            
            elif any(term in category_name for term in ['savasana', 'mindfulness']):
                warnings.append(f"⚠️ Vinyasa Warning: Adding vinyasa transitions after '{category_display}' (relaxation) may disrupt the calming flow. Consider placing vinyasa between active poses instead.")
        
        return warnings

@admin.register(MotivationalQuote)
class MotivationalQuoteAdmin(admin.ModelAdmin):
    list_display = ['training_type', 'quote_preview', 'target_category_display', 'is_exercise_specific', 'times_used', 'is_active']
    list_filter = ['training_type', 'is_exercise_specific', 'target_category__training_type', 'is_active']
    search_fields = ['quote_text']
    readonly_fields = ['times_used', 'last_used', 'is_exercise_specific']
    
    fieldsets = (
        ('Quote Content', {
            'fields': ('training_type', 'quote_text', 'language'),
            'description': 'The motivational quote and what sport it\'s for.'
        }),
        ('Exercise Targeting', {
            'fields': ('target_category',),
            'description': 'Link to specific exercise (leave blank for general quotes).'
        }),
        ('Management', {
            'fields': ('is_active',),
            'description': 'Quote settings and status.'
        }),
        ('Automatic Tracking', {
            'fields': ('is_exercise_specific', 'times_used', 'last_used'),
            'classes': ('collapse',),
            'description': 'System-managed fields (read-only).'
        }),
    )
    
    def quote_preview(self, obj):
        return obj.quote_text[:50] + "..." if len(obj.quote_text) > 50 else obj.quote_text
    quote_preview.short_description = 'Quote Preview'
    
    def target_category_display(self, obj):
        return obj.target_category.display_name if obj.target_category else "General"
    target_category_display.short_description = 'Target Exercise'
    
    def get_form(self, request, obj=None, **kwargs):
        """Filter target_category choices based on training_type"""
        form = super().get_form(request, obj, **kwargs)
        if 'target_category' in form.base_fields:
            if obj:  # Editing existing quote
                form.base_fields['target_category'].queryset = ScriptCategory.objects.filter(
                    training_type=obj.training_type,
                    is_active=True
                ).order_by('display_name')
            else:  # Creating new quote
                form.base_fields['target_category'].queryset = ScriptCategory.objects.filter(
                    is_active=True
                ).order_by('training_type', 'display_name')
        return form
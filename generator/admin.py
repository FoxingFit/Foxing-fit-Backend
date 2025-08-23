from django.contrib import admin
from .models import WorkoutSession, SessionScript

class SessionScriptInline(admin.TabularInline):
    model = SessionScript
    extra = 0
    readonly_fields = ['workout_script', 'sequence_order', 'is_sport_addition']

@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'training_type', 'goal', 'total_duration', 'created_at'
    ]
    list_filter = ['training_type', 'goal', 'is_used', 'created_at']
    search_fields = ['title', 'notes']
    readonly_fields = ['created_at', 'total_duration', 'target_duration', 'time_flexibility']
    inlines = [SessionScriptInline]
    
    fieldsets = (
        ('Workout Information', {
            'fields': ('title', 'training_type', 'goal', 'total_duration'),
            'description': 'Basic information about this generated workout.'
        }),
        ('Generation Settings', {
            'fields': ('target_duration', 'time_flexibility'),
            'description': 'Duration targets and flexibility settings used.'
        }),
        ('Smart Automation Applied', {
            'fields': ('sport_additions_applied',),
            'classes': ('collapse',),
            'description': 'What smart features were automatically applied.'
        }),
        ('Generated Content', {
            'fields': ('compiled_script',),
            'classes': ('collapse',),
            'description': 'The complete generated workout script.'
        }),
        ('Your Usage', {
            'fields': ('is_used', 'notes'),
            'description': 'Track whether you\'ve used this workout and add notes.'
        }),
        ('System Info', {
            'fields': ('created_at',),
            'classes': ('collapse',),
            'description': 'System tracking information.'
        }),
    )
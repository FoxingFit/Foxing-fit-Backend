from django.contrib import admin
from django.utils.html import format_html
from .models import WorkoutSession, SessionScript, AudioPlaylist, AudioSegment

class SessionScriptInline(admin.TabularInline):
    model = SessionScript
    extra = 0
    readonly_fields = ['workout_script', 'sequence_order', 'is_sport_addition']

@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'training_type', 'goal', 'total_duration', 'audio_status', 'created_at'
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
    
    def audio_status(self, obj):
        """Show audio playlist availability"""
        playlists = obj.audio_playlists.all()
        if not playlists.exists():
            return format_html('<span style="color: #9E9E9E;">⚪ No audio</span>')
        
        status_parts = []
        for playlist in playlists:
            completeness = playlist.get_completeness_percentage()
            if completeness == 100:
                status_parts.append(f'<span style="color: #4CAF50;">🎵 {playlist.get_language_display()}</span>')
            elif completeness > 0:
                status_parts.append(f'<span style="color: #FF9800;">🎵 {playlist.get_language_display()} ({completeness:.0f}%)</span>')
            else:
                status_parts.append(f'<span style="color: #9E9E9E;">⚪ {playlist.get_language_display()}</span>')
        
        return format_html(' | '.join(status_parts))
    audio_status.short_description = 'Audio'


@admin.register(AudioPlaylist)
class AudioPlaylistAdmin(admin.ModelAdmin):
    list_display = ['id', 'workout_session', 'language', 'completeness_indicator', 'total_duration', 'created_at']
    list_filter = ['language', 'created_at']
    search_fields = ['workout_session__title']
    readonly_fields = ['total_duration', 'segment_count', 'available_segment_count', 'created_at']
    
    fieldsets = (
        ('Playlist Information', {
            'fields': ('workout_session', 'language'),
            'description': 'Which workout and language this audio playlist is for.'
        }),
        ('Playlist Statistics', {
            'fields': ('total_duration', 'segment_count', 'available_segment_count', 'created_at'),
            'description': 'Automatically calculated playlist metrics.'
        }),
    )
    
    def completeness_indicator(self, obj):
        """Show completeness percentage with visual indicator"""
        percentage = float(obj.get_completeness_percentage())
        if percentage == 100:
            return format_html('<span style="color: #4CAF50; font-weight: bold;">✅ {}% Complete</span>', int(percentage))
        elif percentage >= 75:
            return format_html('<span style="color: #8BC34A;">🟢 {}% Complete</span>', int(percentage))
        elif percentage >= 50:
            return format_html('<span style="color: #FF9800;">🟡 {}% Complete</span>', int(percentage))
        elif percentage > 0:
            return format_html('<span style="color: #F44336;">🔴 {}% Complete</span>', int(percentage))
        else:
            return format_html('<span style="color: #9E9E9E;">⚪ 0% Complete</span>')
    completeness_indicator.short_description = 'Completeness'


@admin.register(AudioSegment)
class AudioSegmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'audio_playlist', 'sequence_order', 'script_title', 'availability_indicator', 'duration', 'pause_after']
    list_filter = ['is_available', 'audio_playlist__language']
    search_fields = ['session_script__workout_script__title']
    readonly_fields = ['audio_playlist', 'session_script', 'sequence_order', 'audio_file', 'duration', 'is_available']
    
    fieldsets = (
        ('Segment Information', {
            'fields': ('audio_playlist', 'session_script', 'sequence_order'),
            'description': 'Which playlist and script this segment belongs to.'
        }),
        ('Audio Details', {
            'fields': ('audio_file', 'duration', 'is_available', 'pause_after'),
            'description': 'Audio file details and pause configuration.'
        }),
    )
    
    def script_title(self, obj):
        """Show the workout script title"""
        return obj.session_script.workout_script.title
    script_title.short_description = 'Script'
    
    def availability_indicator(self, obj):
        """Show availability status"""
        if obj.is_available:
            return format_html('<span style="color: #4CAF50;">✅ Available</span>')
        else:
            return format_html('<span style="color: #F44336;">❌ Missing</span>')
    availability_indicator.short_description = 'Status'
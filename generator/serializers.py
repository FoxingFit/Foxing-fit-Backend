from rest_framework import serializers
from .models import WorkoutSession, SessionScript, AudioPlaylist, AudioSegment
from scripts.serializers import WorkoutScriptSerializer

class SessionScriptSerializer(serializers.ModelSerializer):
    workout_script = WorkoutScriptSerializer(read_only=True)
    
    class Meta:
        model = SessionScript
        fields = ['sequence_order', 'workout_script', 'is_sport_addition']


class AudioSegmentSerializer(serializers.ModelSerializer):
    """Serializer for individual audio segments"""
    script_title = serializers.CharField(source='session_script.workout_script.title', read_only=True)
    script_id = serializers.IntegerField(source='session_script.workout_script.id', read_only=True)
    audio_url = serializers.SerializerMethodField()
    
    class Meta:
        model = AudioSegment
        fields = [
            'id', 'sequence_order', 'script_title', 'script_id',
            'duration', 'is_available', 'pause_after', 'audio_url'
        ]
    
    def get_audio_url(self, obj):
        """Get URL for audio file if available"""
        if obj.is_available and obj.audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.audio_file.url)
        return None


class AudioPlaylistSerializer(serializers.ModelSerializer):
    """Serializer for audio playlists"""
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    completeness_percentage = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    segments = AudioSegmentSerializer(many=True, read_only=True)
    workout_session_id = serializers.IntegerField(source='workout_session.id', read_only=True)
    merged_audio_url = serializers.SerializerMethodField()
    has_merged_audio = serializers.SerializerMethodField()
    
    class Meta:
        model = AudioPlaylist
        fields = [
            'id', 'workout_session_id', 'language', 'language_display',
            'total_duration', 'segment_count', 'available_segment_count',
            'completeness_percentage', 'is_complete', 'created_at', 'segments',
            'merged_audio_url', 'has_merged_audio', 'merged_at'
        ]
    
    def get_completeness_percentage(self, obj):
        """Get completeness percentage"""
        return obj.get_completeness_percentage()
    
    def get_is_complete(self, obj):
        """Check if playlist is complete"""
        return obj.is_complete()
    
    def get_merged_audio_url(self, obj):
        """Get URL for merged audio file if available"""
        if obj.merged_audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.merged_audio_file.url)
        return None
    
    def get_has_merged_audio(self, obj):
        """Check if merged audio exists"""
        return bool(obj.merged_audio_file)


class WorkoutSessionSerializer(serializers.ModelSerializer):
    training_type_display = serializers.CharField(source='get_training_type_display', read_only=True)
    goal_display = serializers.CharField(source='get_goal_display', read_only=True)
    time_status = serializers.CharField(source='get_time_status', read_only=True)
    sport_logic_summary = serializers.CharField(source='get_sport_logic_summary', read_only=True)
    session_scripts = SessionScriptSerializer(many=True, read_only=True)
    audio_playlists = AudioPlaylistSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkoutSession
        fields = '__all__'
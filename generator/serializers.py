from rest_framework import serializers
from .models import WorkoutSession, SessionScript, SessionQuote, AudioPlaylist, AudioSegment, AudioQuoteSegment
from scripts.serializers import WorkoutScriptSerializer

class SessionScriptSerializer(serializers.ModelSerializer):
    workout_script = WorkoutScriptSerializer(read_only=True)
    
    class Meta:
        model = SessionScript
        fields = ['sequence_order', 'workout_script', 'is_sport_addition']


class SessionQuoteSerializer(serializers.ModelSerializer):
    """Serializer for session quotes"""
    quote_text = serializers.CharField(source='motivational_quote.quote_text', read_only=True)
    quote_id = serializers.IntegerField(source='motivational_quote.id', read_only=True)
    inserted_after_script_title = serializers.CharField(
        source='inserted_after_script.workout_script.title', 
        read_only=True
    )
    
    class Meta:
        model = SessionQuote
        fields = ['sequence_order', 'quote_text', 'quote_id', 'inserted_after_script_title']


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
        if not obj.is_available:
            return None
        
        # Get audio file from the related WorkoutScript
        language = obj.audio_playlist.language
        workout_script = obj.session_script.workout_script
        audio_file = workout_script.get_audio_file(language)
        
        if audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(audio_file.url)
        return None


class AudioQuoteSegmentSerializer(serializers.ModelSerializer):
    """Serializer for audio quote segments"""
    quote_text = serializers.CharField(source='session_quote.motivational_quote.quote_text', read_only=True)
    quote_id = serializers.IntegerField(source='session_quote.motivational_quote.id', read_only=True)
    audio_url = serializers.SerializerMethodField()
    
    class Meta:
        model = AudioQuoteSegment
        fields = [
            'id', 'sequence_order', 'quote_text', 'quote_id',
            'duration', 'is_available', 'pause_after', 'audio_url'
        ]
    
    def get_audio_url(self, obj):
        """Get URL for audio file if available"""
        if not obj.is_available:
            return None
        
        # Get audio file from the related MotivationalQuote
        language = obj.audio_playlist.language
        motivational_quote = obj.session_quote.motivational_quote
        audio_file = motivational_quote.get_audio_file(language)
        
        if audio_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(audio_file.url)
        return None


class AudioPlaylistSerializer(serializers.ModelSerializer):
    """Serializer for audio playlists with both script and quote segments"""
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    completeness_percentage = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    segments = AudioSegmentSerializer(many=True, read_only=True)
    quote_segments = AudioQuoteSegmentSerializer(many=True, read_only=True)
    all_segments = serializers.SerializerMethodField()
    workout_session_id = serializers.IntegerField(source='workout_session.id', read_only=True)
    merged_audio_url = serializers.SerializerMethodField()
    has_merged_audio = serializers.SerializerMethodField()
    
    class Meta:
        model = AudioPlaylist
        fields = [
            'id', 'workout_session_id', 'language', 'language_display',
            'total_duration', 'segment_count', 'available_segment_count',
            'completeness_percentage', 'is_complete', 'created_at', 
            'segments', 'quote_segments', 'all_segments',
            'merged_audio_url', 'has_merged_audio', 'merged_at'
        ]
    
    def get_completeness_percentage(self, obj):
        """Get completeness percentage"""
        return obj.get_completeness_percentage()
    
    def get_is_complete(self, obj):
        """Check if playlist is complete"""
        return obj.is_complete()
    
    def get_all_segments(self, obj):
        """Get all segments (scripts + quotes) sorted by sequence order"""
        request = self.context.get('request')
        
        # Serialize script segments
        script_segments = AudioSegmentSerializer(
            obj.segments.all(), 
            many=True, 
            context={'request': request}
        ).data
        
        # Serialize quote segments
        quote_segments = AudioQuoteSegmentSerializer(
            obj.quote_segments.all(), 
            many=True, 
            context={'request': request}
        ).data
        
        # Combine and sort by sequence order
        all_segments = script_segments + quote_segments
        all_segments.sort(key=lambda x: x['sequence_order'])
        
        return all_segments
    
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
    session_quotes = SessionQuoteSerializer(many=True, read_only=True)
    audio_playlists = AudioPlaylistSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkoutSession
        fields = '__all__'
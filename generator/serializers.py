from rest_framework import serializers
from .models import WorkoutSession, SessionScript
from scripts.serializers import WorkoutScriptSerializer

class SessionScriptSerializer(serializers.ModelSerializer):
    workout_script = WorkoutScriptSerializer(read_only=True)
    
    class Meta:
        model = SessionScript
        fields = ['sequence_order', 'workout_script', 'is_sport_addition']

class WorkoutSessionSerializer(serializers.ModelSerializer):
    training_type_display = serializers.CharField(source='get_training_type_display', read_only=True)
    goal_display = serializers.CharField(source='get_goal_display', read_only=True)
    time_status = serializers.CharField(source='get_time_status', read_only=True)
    sport_logic_summary = serializers.CharField(source='get_sport_logic_summary', read_only=True)
    session_scripts = SessionScriptSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkoutSession
        fields = '__all__'
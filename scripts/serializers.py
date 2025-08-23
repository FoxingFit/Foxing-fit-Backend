from rest_framework import serializers
from .models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory

class ScriptCategorySerializer(serializers.ModelSerializer):
    training_type_display = serializers.CharField(source='get_training_type_display', read_only=True)
    
    class Meta:
        model = ScriptCategory
        fields = '__all__'

class WorkoutScriptSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    script_category_display = serializers.CharField(source='script_category.display_name', read_only=True)
    goal_display = serializers.CharField(source='get_goal_display', read_only=True)
    intensity_display = serializers.CharField(source='get_intensity_level_display', read_only=True)
    freshness_score = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkoutScript
        fields = '__all__'
    
    def get_freshness_score(self, obj):
        return obj.get_freshness_score()

class MotivationalQuoteSerializer(serializers.ModelSerializer):
    training_type_display = serializers.CharField(source='get_training_type_display', read_only=True)
    target_category_display = serializers.SerializerMethodField()
    formatted_quote = serializers.CharField(source='get_formatted_quote', read_only=True)
    
    class Meta:
        model = MotivationalQuote
        fields = '__all__'
    
    def get_target_category_display(self, obj):
        return obj.target_category.display_name if obj.target_category else "General"

class WorkoutTemplateSerializer(serializers.ModelSerializer):
    primary_category_display = serializers.CharField(source='primary_category.display_name', read_only=True)
    alternative_categories_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkoutTemplate
        fields = '__all__'
    
    def get_alternative_categories_display(self, obj):
        return [alt.display_name for alt in obj.alternative_categories.all()]
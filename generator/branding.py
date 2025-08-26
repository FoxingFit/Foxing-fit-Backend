class FoxingFitBranding:
    """
    Handles standardized Foxing Fit opening/closing texts and round number formatting
    """
    
    OPENING_TEXTS = {
        'kickboxing': "Get ready to start your Foxing Fit Heavybag Training.",
        'power_yoga': "Get ready to start your Foxing Fit Power Yoga Lesson.",
        'calisthenics': "Get ready to start your Foxing Fit Calisthenics workout."
    }
    
    CLOSING_TEXTS = {
        'kickboxing': "Stay Sharp, Stay Foxing Fit.",
        'power_yoga': "Stay Flexible, Stay Foxing Fit.",
        'calisthenics': "Stay Strong, Stay Foxing Fit."
    }
    
    @classmethod
    def get_opening_text(cls, training_type):
        """Get standardized opening text for sport"""
        return cls.OPENING_TEXTS.get(training_type, "Get ready to start your Foxing Fit workout.")
    
    @classmethod
    def get_closing_text(cls, training_type):
        """Get standardized closing text for sport"""
        return cls.CLOSING_TEXTS.get(training_type, "Stay Fit, Stay Foxing Fit.")
    
    @classmethod
    def format_round_header(cls, round_number, script_title, training_type='nl'):
        """
        Format round header in simple text format (NO orange styling)
        
        Args:
            round_number: The round number (1, 2, 3, etc.)
            script_title: The script title (already cleaned of round numbers)
            training_type: Language preference ('nl' for Dutch, 'en' for English)
        
        Returns:
            Formatted round header in simple text format
        """
        if training_type == 'en':
            round_text = f"Round {round_number}: {script_title}"
        else:
            # Default to Dutch as Johnny's preference
            round_text = f"Ronde {round_number}: {script_title}"
        
        # Return in simple text format (no HTML styling)
        return round_text
    
    @classmethod
    def format_special_round_header(cls, special_type, script_title=None):
        """
        Format special round headers (surprise, MAX challenge, vinyasa)
        
        Args:
            special_type: Type of special round ('surprise', 'max_challenge', 'vinyasa')
            script_title: Optional script title to include
        
        Returns:
            Formatted special round header with appropriate styling and emoji
        """
        headers = {
            'surprise': "🎯 SURPRISE RONDE",
            'max_challenge': "💪 MAX CHALLENGE",
            'vinyasa_s2s': "🌊 VINYASA OVERGANG (Staand naar Staand)",
            'vinyasa_s2sit': "🌊 VINYASA OVERGANG (Staand naar Zittend)", 
            'vinyasa': "🌊 VINYASA OVERGANG"
        }
        
        header = headers.get(special_type, f"✨ {special_type.upper()}")
        
        if script_title:
            return f"{header}: {script_title}"
        else:
            return header
    
    @classmethod
    def should_use_round_numbering(cls, script_category_name):
        """
        ALL scripts get round numbers EXCEPT special rounds
        """
        # Only these special categories should NOT get round numbers
        no_round_categories = [
            'surprise', 'vinyasa', 'max'
        ]
        
        category_lower = script_category_name.lower()
        
        # If it contains any special keywords, no round number
        return not any(pattern in category_lower for pattern in no_round_categories)
    

    @classmethod
    def detect_special_round_type(cls, script):
        """
        Detect what type of special round a script is
        """
        if script.is_surprise_round():
            return 'surprise'
        elif script.is_max_challenge():
            return 'max_challenge'
        elif script.is_vinyasa_transition():
            category_name = script.script_category.name.lower()
            if 's2s' in category_name:
                return 'vinyasa_s2s'
            elif 's2sit' in category_name:
                return 'vinyasa_s2sit'
            else:
                return 'vinyasa'
        
        return None
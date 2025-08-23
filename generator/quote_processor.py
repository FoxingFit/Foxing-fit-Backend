import re
import random
from scripts.models import MotivationalQuote

class QuoteProcessor:
    """
    Handles intelligent quote replacement in workout scripts respecting Johnny's rules
    
    Key Features:
    - Only replaces existing [Onthoud,..] placeholders
    - Never adds quotes where none existed
    - Matches exercise-specific quotes to relevant scripts
    - Tracks usage to prevent repetition
    - Respects Johnny's placement rules
    """
    
    def __init__(self):
        self.used_quote_ids = set()
    
    def process_script_content(self, script, training_type):
        """
        Process a single script's content to replace quote placeholders
        
        Args:
            script: WorkoutScript instance
            training_type: Sport type for quote selection
            
        Returns:
            Processed content with quotes filled in or placeholders removed
        """
        content = script.content
        
        # Find all quote placeholders
        placeholder_pattern = r'\[\s*Onthoud\s*,\s*\.+\s*\]'
        placeholders = re.findall(placeholder_pattern, content)
        
        if not placeholders:
            return content  # No placeholders = no changes
        
        # Replace each placeholder with appropriate quote
        for placeholder in placeholders:
            quote = self._select_contextual_quote(script, training_type)
            if quote:
                formatted_quote = f"**{quote.get_formatted_quote()}**"
                content = content.replace(placeholder, formatted_quote, 1)
                quote.mark_used()
                self.used_quote_ids.add(quote.id)
            else:
                # Remove placeholder if no suitable quote found
                content = content.replace(placeholder, '', 1)
        
        return content
    
    def _select_contextual_quote(self, script, training_type):
        """
        Select the best quote for this script's context using foreign key matching
        
        Priority:
        1. Exercise-specific quotes for this exact category
        2. General quotes for this sport
        3. Return None if no suitable quotes
        """
        
        # Get all available quotes for this sport that are active
        available_quotes = MotivationalQuote.objects.filter(
            training_type=training_type,
            is_active=True
        ).exclude(id__in=self.used_quote_ids)
        
        if not available_quotes.exists():
            return None
        
        # Priority 1: Exercise-specific quotes for this exact category
        category_quotes = available_quotes.filter(
            is_exercise_specific=True,
            target_category=script.script_category  # Direct foreign key match!
        ).order_by('times_used', 'last_used')  # Prefer less used quotes
        
        if category_quotes.exists():
            return category_quotes.first()
        
        # Priority 2: General quotes (no specific category)
        general_quotes = available_quotes.filter(
            is_exercise_specific=False,
            target_category__isnull=True  # No specific category
        ).order_by('times_used', 'last_used')  # Prefer less used quotes
        
        if general_quotes.exists():
            # Add some randomization among top 3 least used
            top_candidates = list(general_quotes[:3])
            return random.choice(top_candidates) if top_candidates else None
        
        return None
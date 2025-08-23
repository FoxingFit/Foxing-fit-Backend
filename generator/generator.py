import random
from django.utils import timezone
from django.db.models import Avg, Q
from scripts.models import WorkoutScript, WorkoutTemplate, MotivationalQuote, ScriptCategory
from .models import WorkoutSession, SessionScript
from .quote_processor import QuoteProcessor
from .branding import FoxingFitBranding

class SportSpecificLogicMixin:
    """Base mixin providing sport-specific intelligence for workout generation"""
    
    def apply_sport_specific_intelligence(self, selected_scripts, training_type, goal):
        """Route to appropriate sport-specific logic based on training type"""
        print(f"🧠 Applying {training_type} sport intelligence...")
        
        if training_type == 'kickboxing':
            return self.apply_kickboxing_intelligence(selected_scripts, goal)
        elif training_type == 'power_yoga':
            return self.apply_power_yoga_intelligence(selected_scripts, goal)
        elif training_type == 'calisthenics':
            return self.apply_calisthenics_intelligence(selected_scripts, goal)
        
        return selected_scripts
    
    def find_special_round_script(self, training_type, script_category):
        """Find a script for the special round category (surprise, MAX challenge, vinyasa)"""
        if not script_category:
            print(f"⚠️ No special category provided for {training_type}")
            return None
        
        print(f"🎯 Looking for special round: {script_category.display_name} ({script_category.name})")
        
        special_scripts = WorkoutScript.objects.filter(
            type=training_type,
            script_category=script_category,
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        print(f"📊 Found {special_scripts.count()} available special scripts")
        
        if special_scripts.exists():
            special_scripts_list = list(special_scripts)
            special_scripts_list.sort(key=lambda s: s.get_freshness_score(), reverse=True)
            selected = special_scripts_list[0]
            
            print(f"✅ Selected special script: '{selected.title}' (goal: {selected.goal}, duration: {selected.duration_minutes}min)")
            
            selected.mark_selected()
            self.used_script_ids.add(selected.id)
            return selected
        else:
            print(f"❌ No available special scripts for {script_category.display_name}")
        
        return None
    
    def track_sport_addition(self, addition_type, count=1):
        """Track sport-specific additions for metadata"""
        if not hasattr(self, 'sport_additions'):
            self.sport_additions = {}
        
        if addition_type not in self.sport_additions:
            self.sport_additions[addition_type] = 0
        self.sport_additions[addition_type] += count
        
        print(f"📈 Tracked sport addition: {addition_type} (+{count})")

class KickboxingIntelligenceMixin(SportSpecificLogicMixin):
    """Kickboxing-specific logic: Automatic surprise round insertion based on admin template choices"""
    
    def apply_kickboxing_intelligence(self, selected_scripts, goal):
        """Process selected scripts - surprise rounds already added via templates"""
        print(f"🥊 Kickboxing intelligence: {len(selected_scripts)} scripts to process")
        return selected_scripts

class PowerYogaIntelligenceMixin(SportSpecificLogicMixin):
    """Power Yoga-specific logic: Admin-controlled vinyasa transitions"""
    
    def apply_power_yoga_intelligence(self, selected_scripts, goal):
        """Process selected scripts - vinyasa transitions already added via templates"""
        print(f"🧘‍♀️ Power Yoga intelligence: {len(selected_scripts)} scripts to process")
        return selected_scripts

class CalisthenicsIntelligenceMixin(SportSpecificLogicMixin):
    """Calisthenics-specific logic: Admin-controlled MAX challenge + logical exercise ordering"""
    
    def apply_calisthenics_intelligence(self, selected_scripts, goal):
        """Apply logical exercise ordering while respecting admin template configuration"""
        print(f"💪 Calisthenics intelligence: Applying logical ordering to {len(selected_scripts)} scripts")
        
        ordered_scripts = self.apply_logical_exercise_ordering(selected_scripts)
        
        if len(ordered_scripts) != len(selected_scripts) or ordered_scripts != selected_scripts:
            self.track_sport_addition('difficulty_reordered')
            print("🔄 Applied difficulty reordering")
        
        return ordered_scripts
    
    def apply_logical_exercise_ordering(self, scripts):
        """Apply logical ordering to calisthenics exercises for safety"""
        warmup_scripts = []
        basic_scripts = []
        advanced_scripts = []
        special_scripts = []
        
        print("📋 Categorizing scripts for logical ordering:")
        
        for script in scripts:
            category_name = script.script_category.name.lower()
            
            if 'warmup' in category_name:
                warmup_scripts.append(script)
                print(f"  🔥 Warmup: {script.title}")
            elif script.is_max_challenge():
                special_scripts.append((len(warmup_scripts + basic_scripts + advanced_scripts), script))
                print(f"  💪 MAX Challenge: {script.title}")
            elif any(advanced_term in category_name for advanced_term in 
                    ['handstand', 'lever', 'planche']):
                advanced_scripts.append(script)
                print(f"  🏆 Advanced: {script.title}")
            else:
                basic_scripts.append(script)
                print(f"  📚 Basic: {script.title}")
        
        ordered_base = warmup_scripts + basic_scripts + advanced_scripts
        
        for position, special_script in special_scripts:
            ordered_base.insert(min(position, len(ordered_base)), special_script)
        
        print(f"✅ Final order: {len(ordered_base)} scripts arranged logically")
        return ordered_base

class IntelligentWorkoutGenerator(
    KickboxingIntelligenceMixin,
    PowerYogaIntelligenceMixin, 
    CalisthenicsIntelligenceMixin
):
    """Johnny's intelligent workout generator with sport-specific logic and flexible duration support"""
    
    def __init__(self):
        """Initialize generator with tracking and constraints"""
        self.selected_scripts = []
        self.used_script_ids = set()
        self.target_duration = 60.0
        self.time_flexibility = 5.0
        self.sport_additions = {}
        self.missing_categories = []  # Track missing categories
        self.fallback_substitutions = []  # Track what substitutions were made
        
    def generate_workout_with_custom_duration(self, training_type, goal='allround', target_duration=60.0):
        """Generate workout with custom duration and sport-specific intelligence"""
        
        print("="*80)
        print(f"🚀 STARTING WORKOUT GENERATION")
        print(f"📋 Sport: {training_type.upper()}")
        print(f"🎯 Goal: {goal.upper()}")  
        print(f"⏰ Target Duration: {target_duration} minutes")
        print("="*80)
        
        self.target_duration = float(target_duration)
        
        if self.target_duration < 15 or self.target_duration > 120:
            raise ValueError("Target duration must be between 15 and 120 minutes")
        
        # Adjust time flexibility based on duration
        if self.target_duration <= 30:
            self.time_flexibility = 3.0
        elif self.target_duration <= 45:
            self.time_flexibility = 4.0
        else:
            self.time_flexibility = 5.0
        
        print(f"⚖️ Time flexibility: ±{self.time_flexibility} minutes")
        
        # Load active template rules for this sport
        template_rules = WorkoutTemplate.objects.filter(
            training_type=training_type
        ).order_by('sequence_order')
        
        print(f"📜 Found {template_rules.count()} template rules for {training_type}")
        
        if not template_rules.exists():
            raise ValueError(f"No workout template defined for {training_type}")
        
        # CRITICAL DEBUG: Show template structure
        print("\n📋 TEMPLATE STRUCTURE:")
        for rule in template_rules:
            alternatives = list(rule.alternative_categories.values_list('display_name', flat=True))
            alt_text = f" OR {', '.join(alternatives)}" if alternatives else ""
            special_text = ""
            if hasattr(rule, 'add_surprise_round_after') and rule.add_surprise_round_after:
                special_text += " +SURPRISE"
            if hasattr(rule, 'add_max_challenge_after') and rule.add_max_challenge_after:
                special_text += " +MAX"
            if hasattr(rule, 'add_vinyasa_transition_after') and rule.add_vinyasa_transition_after:
                special_text += f" +VINYASA({rule.vinyasa_type})"
            
            print(f"  {rule.sequence_order}. {rule.primary_category.display_name}{alt_text} {'(REQUIRED)' if rule.is_required else '(OPTIONAL)'}{special_text}")
        
        # Generate base workout following template rules with improved logic
        selected_scripts = self.generate_base_workout_from_templates(
            template_rules, training_type, goal
        )
        
        print(f"\n📊 BASE GENERATION COMPLETE: {len(selected_scripts)} scripts selected")
        
        # Apply sport-specific post-processing
        enhanced_scripts = self.apply_sport_specific_intelligence(
            selected_scripts, training_type, goal
        )
        
        print(f"🧠 SPORT INTELLIGENCE COMPLETE: {len(enhanced_scripts)} scripts after processing")
        
        # Apply duration management
        final_scripts = self.apply_duration_management(
            enhanced_scripts, training_type, goal
        )
        
        print(f"⏰ DURATION MANAGEMENT COMPLETE: {len(final_scripts)} final scripts")
        
        if not final_scripts:
            raise ValueError("No suitable scripts found for workout generation")
        
        # Show final workout structure
        print("\n🏁 FINAL WORKOUT STRUCTURE:")
        total_duration = 0
        for i, script in enumerate(final_scripts, 1):
            total_duration += script.duration_minutes
            special_indicator = ""
            if script.is_surprise_round():
                special_indicator = " 🎯"
            elif script.is_max_challenge():
                special_indicator = " 💪"
            elif script.is_vinyasa_transition():
                special_indicator = " 🌊"
            
            print(f"  {i}. {script.script_category.display_name}: {script.title}{special_indicator}")
            print(f"     Goal: {script.goal} | Duration: {script.duration_minutes}min")
        
        print(f"\n⏰ Total Duration: {total_duration:.1f} minutes")
        print(f"🎯 Target: {self.target_duration} ± {self.time_flexibility} minutes")
        
        # Create and save workout session
        workout_session = self.create_workout_session_record(
            final_scripts, training_type, goal
        )
        
        print(f"💾 Workout saved with ID: {workout_session.id}")
        print("="*80)
        
        return self.compile_generation_results(workout_session, final_scripts, training_type)
    
    def generate_base_workout_from_templates(self, template_rules, training_type, goal):
        """Enhanced template processing with required step priority and budget planning"""
        
        print(f"\n🏗️ ENHANCED TEMPLATE PROCESSING START")
        print(f"Processing {template_rules.count()} template rules with required step priority...")
        
        selected_scripts = []
        total_duration = 0
        min_duration = self.target_duration - self.time_flexibility
        max_duration = self.target_duration + self.time_flexibility
        
        # PHASE 1: BUDGET PLANNING - Calculate required steps minimum duration
        print(f"\n💰 PHASE 1: BUDGET PLANNING")
        print(f"=" * 40)
        
        required_steps = [t for t in template_rules if t.is_required and t.is_active]
        optional_steps = [t for t in template_rules if not t.is_required and t.is_active]
        
        print(f"📊 Found {len(required_steps)} required steps, {len(optional_steps)} optional steps")
        
        # Estimate minimum duration needed for required steps
        estimated_required_duration = self._estimate_required_steps_duration(
            required_steps, training_type, goal
        )
        
        # Calculate budget available for optional steps
        optional_budget = max_duration - estimated_required_duration
        print(f"⏰ Estimated required duration: {estimated_required_duration:.1f} minutes")
        print(f"💰 Optional budget available: {optional_budget:.1f} minutes")
        
        if optional_budget < 0:
            print(f"⚠️ WARNING: Required steps may exceed target duration by {abs(optional_budget):.1f} minutes")
            optional_budget = 0
        
        # PHASE 2: SEQUENTIAL PROCESSING with Budget Control
        print(f"\n🎯 PHASE 2: SEQUENTIAL PROCESSING WITH BUDGET CONTROL")
        print(f"=" * 60)
        
        optional_used = 0
        
        for i, template_rule in enumerate(template_rules, 1):
            print(f"\n--- TEMPLATE STEP {template_rule.sequence_order} ---")
            print(f"🎯 Processing: {template_rule.primary_category.display_name}")
            print(f"📋 Type: {'REQUIRED' if template_rule.is_required else 'OPTIONAL'}")
            print(f"⏰ Current duration: {total_duration:.1f}min / {max_duration:.1f}min max")
            
            if not template_rule.is_active:
                print(f"⏭️ SKIPPED: Template step is inactive")
                continue
            
            # Get all possible categories for this template step
            possible_categories = template_rule.get_all_possible_categories()
            active_categories = [cat for cat in possible_categories if cat.is_active]
            
            print(f"📂 Possible categories ({len(active_categories)} active):")
            for cat in active_categories:
                script_count = WorkoutScript.objects.filter(
                    type=training_type,
                    script_category=cat,
                    is_active=True
                ).exclude(id__in=self.used_script_ids).count()
                print(f"  • {cat.display_name} ({cat.name}) - {script_count} available scripts")
            
            if not active_categories:
                print("❌ No active categories available for this step")
                if template_rule.is_required:
                    print("⚠️ This was a REQUIRED step - trying regular exercise fallback...")
                    self._handle_missing_required_step(template_rule, selected_scripts, training_type, goal, max_duration - total_duration)
                continue
            
            # BUDGET CHECK: Different logic for required vs optional
            if template_rule.is_required:
                # REQUIRED: Always try to fulfill, but warn if tight on time
                remaining_time = max_duration - total_duration
                if remaining_time < 3:
                    print(f"⚠️ TIGHT TIME: Only {remaining_time:.1f}min left for required step")
                    
                selected_script = self.select_best_script_from_categories(
                    active_categories, goal, training_type, remaining_time
                )
                
            else:
                # OPTIONAL: Check budget first
                remaining_optional_budget = optional_budget - optional_used
                remaining_total_time = max_duration - total_duration
                
                # Use the smaller of the two constraints
                available_time = min(remaining_optional_budget, remaining_total_time)
                
                print(f"💰 Optional budget check:")
                print(f"   Remaining optional budget: {remaining_optional_budget:.1f}min")
                print(f"   Remaining total time: {remaining_total_time:.1f}min")
                print(f"   Available for this optional: {available_time:.1f}min")
                
                if available_time < 3:  # Need at least 3 minutes for a meaningful script
                    print(f"⏭️ SKIPPED OPTIONAL: Insufficient budget ({available_time:.1f}min < 3min)")
                    continue
                    
                selected_script = self.select_best_script_from_categories(
                    active_categories, goal, training_type, available_time
                )
            
            # Process the selected script
            if selected_script:
                success_type = "REQUIRED" if template_rule.is_required else "OPTIONAL"
                print(f"✅ {success_type} SELECTED: '{selected_script.title}'")
                print(f"   Category: {selected_script.script_category.display_name}")
                print(f"   Goal: {selected_script.goal} (requested: {goal})")
                print(f"   Duration: {selected_script.duration_minutes}min")
                
                selected_scripts.append(selected_script)
                total_duration += selected_script.duration_minutes
                self.used_script_ids.add(selected_script.id)
                selected_script.mark_selected()
                
                # Track optional budget usage
                if not template_rule.is_required:
                    optional_used += selected_script.duration_minutes
                    print(f"   💰 Optional budget used: {optional_used:.1f}/{optional_budget:.1f}min")
                
                # Process special rounds
                self._process_special_rounds_after_step(template_rule, selected_scripts, total_duration, training_type)
                # Update total_duration after special rounds
                total_duration = sum(script.duration_minutes for script in selected_scripts)
                
            elif template_rule.is_required:
                print(f"❌ FAILED to find script for REQUIRED step: {template_rule.primary_category.display_name}")
                self._handle_missing_required_step(template_rule, selected_scripts, training_type, goal, max_duration - total_duration)
                # Update total_duration after fallback
                total_duration = sum(script.duration_minutes for script in selected_scripts)
            else:
                print(f"⏭️ SKIPPED optional step: {template_rule.primary_category.display_name}")
        
        # PHASE 3: SUMMARY
        print(f"\n📊 BUDGET PLANNING RESULTS:")
        print(f"✅ Total duration: {total_duration:.1f} minutes")
        print(f"💰 Optional budget used: {optional_used:.1f}/{optional_budget:.1f} minutes")
        print(f"🎯 Target range: {min_duration:.1f}-{max_duration:.1f} minutes")
        
        if total_duration < min_duration:
            shortage = min_duration - total_duration
            print(f"📈 Workout short by {shortage:.1f}min - will add filler content")
        elif total_duration > max_duration:
            excess = total_duration - max_duration
            print(f"📉 Workout long by {excess:.1f}min - will trim content")
        else:
            print(f"✅ Perfect duration within target range")
        
        # Show missing categories summary
        if self.missing_categories:
            print(f"\n⚠️ MISSING CONTENT SUMMARY:")
            print(f"The following categories need scripts to be added:")
            for missing in self.missing_categories:
                print(f"  ❌ {missing['category']} ({missing['name']})")
            
            if self.fallback_substitutions:
                print(f"\n🔄 SUBSTITUTIONS MADE:")
                for sub in self.fallback_substitutions:
                    print(f"  • {sub['missing']} → {sub['used']}: '{sub['script']}'")
        
        print(f"\n🏗️ ENHANCED TEMPLATE PROCESSING COMPLETE")
        print(f"📊 Generated {len(selected_scripts)} scripts with required step priority")
        
        return selected_scripts
    
    def _estimate_required_steps_duration(self, required_steps, training_type, goal):
        """Estimate minimum duration needed for all required steps"""
        
        print(f"🔍 Estimating required steps duration:")
        total_estimated = 0
        
        for step in required_steps:
            possible_categories = step.get_all_possible_categories()
            
            # Find shortest script in any of the possible categories
            shortest_script = WorkoutScript.objects.filter(
                type=training_type,
                script_category__in=possible_categories,
                is_active=True
            ).exclude(id__in=self.used_script_ids).order_by('duration_minutes').first()
            
            if shortest_script:
                step_duration = shortest_script.duration_minutes
            else:
                # Fallback estimate if no scripts found
                step_duration = 5.0  # Conservative 5-minute estimate
            
            # Add potential special round duration
            special_category = step.get_special_round_category_to_add_after()
            if special_category:
                special_script = WorkoutScript.objects.filter(
                    type=training_type,
                    script_category=special_category,
                    is_active=True
                ).order_by('duration_minutes').first()
                
                if special_script:
                    step_duration += special_script.duration_minutes
                else:
                    step_duration += 3.5  # Conservative estimate for special rounds
            
            total_estimated += step_duration
            print(f"   📋 {step.primary_category.display_name}: ~{step_duration:.1f}min")
        
        return total_estimated
    
    def _handle_missing_required_step(self, template_rule, selected_scripts, training_type, goal, max_remaining_duration):
        """Handle missing required steps with fallback logic"""
        
        print("🔄 Trying regular exercise fallback for required step...")
        
        # Record missing category
        self.missing_categories.append({
            'category': template_rule.primary_category.display_name,
            'name': template_rule.primary_category.name,
            'required': True
        })
        
        # Try fallback with remaining duration constraint
        fallback_script = self.find_fallback_script_for_training_type(
            training_type, goal, max_remaining_duration
        )
        
        if fallback_script:
            print(f"✅ REQUIRED FALLBACK: '{fallback_script.title}' ({fallback_script.script_category.display_name})")
            
            # Record the substitution
            self.fallback_substitutions.append({
                'missing': template_rule.primary_category.display_name,
                'used': fallback_script.script_category.display_name,
                'script': fallback_script.title
            })
            
            selected_scripts.append(fallback_script)
            self.used_script_ids.add(fallback_script.id)
            fallback_script.mark_selected()
        else:
            print("❌ No fallback available - required step will be missing from workout")
    
    def _process_special_rounds_after_step(self, template_rule, selected_scripts, current_duration, training_type):
        """Process special rounds that should be added after this step"""
        
        print(f"🔍 Checking for special rounds after this step...")
        
        special_category = template_rule.get_special_round_category_to_add_after()
        
        if special_category and special_category.is_active:
            print(f"🎯 Template requests special round: {special_category.display_name}")
            special_script = self.find_special_round_script(training_type, special_category)
            if special_script:
                selected_scripts.append(special_script)
                
                # Track the type of special addition
                if special_script.is_surprise_round():
                    self.track_sport_addition('surprise_rounds_added')
                    print(f"🎯 Added surprise round: {special_script.title}")
                elif special_script.is_max_challenge():
                    self.track_sport_addition('max_challenge_added')
                    print(f"💪 Added MAX challenge: {special_script.title}")
                elif special_script.is_vinyasa_transition():
                    self.track_sport_addition('vinyasa_transitions_added')
                    print(f"🌊 Added vinyasa transition: {special_script.title}")
        else:
            print("ℹ️ No special rounds requested for this step")
    
    def select_best_script_from_categories(self, possible_categories, goal, training_type, max_remaining_duration):
        """Select best script from possible categories using goal fallback algorithm"""
        
        print(f"🔍 Selecting script from {len(possible_categories)} possible categories...")
        print(f"   Requested goal: {goal}")
        print(f"   Max remaining time: {max_remaining_duration:.1f}min")
        
        for i, category in enumerate(possible_categories, 1):
            print(f"\n  Trying category {i}/{len(possible_categories)}: {category.display_name}")
            
            script = self.select_best_script_for_category(
                category, goal, training_type, max_remaining_duration
            )
            if script:
                print(f"  ✅ Found script in {category.display_name}")
                return script
            else:
                print(f"  ❌ No suitable script in {category.display_name}")
        
        print(f"❌ No suitable script found in any of the {len(possible_categories)} categories")
        return None
    
    def select_best_script_for_category(self, script_category, goal, training_type, max_duration=None):
        """Select best script for category using goal fallback: try requested goal first, then any goal"""
        
        print(f"    🎯 Searching in category: {script_category.display_name} ({script_category.name})")
        
        # Phase 1: Try to find script in user's requested goal
        print(f"    Phase 1: Looking for goal '{goal}' or 'allround'...")
        
        primary_candidates = WorkoutScript.objects.filter(
            type=training_type,
            script_category=script_category,
            goal__in=[goal, 'allround'],
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        if max_duration is not None:
            primary_candidates = primary_candidates.filter(duration_minutes__lte=max_duration)
            print(f"    Applied duration filter: ≤{max_duration:.1f}min")
        
        print(f"    Found {primary_candidates.count()} scripts matching requested goal")
        
        if primary_candidates.exists():
            selected = self._select_from_candidates_using_freshness(primary_candidates)
            print(f"    ✅ Phase 1 SUCCESS: Selected '{selected.title}' (goal: {selected.goal})")
            return selected
        
        # Phase 2: Goal fallback - try any goal to fulfill template requirement
        print(f"    Phase 2: Goal fallback - looking for ANY goal...")
        
        fallback_candidates = WorkoutScript.objects.filter(
            type=training_type,
            script_category=script_category,
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        if max_duration is not None:
            fallback_candidates = fallback_candidates.filter(duration_minutes__lte=max_duration)
        
        print(f"    Found {fallback_candidates.count()} scripts with any goal")
        
        if fallback_candidates.exists():
            # Show available goals for debugging
            available_goals = list(fallback_candidates.values_list('goal', flat=True).distinct())
            print(f"Available goals: {available_goals}")
            
            selected = self._select_from_candidates_using_freshness(fallback_candidates)
            print(f"    ✅ Phase 2 SUCCESS: Selected '{selected.title}' (goal: {selected.goal}) - GOAL FALLBACK USED")
            return selected
        
        print(f"    ❌ No scripts found in category {script_category.display_name}")
        return None
    
    def _select_from_candidates_using_freshness(self, candidates):
        """Select from candidates using freshness algorithm"""
        candidates_list = list(candidates)
        candidates_list.sort(key=lambda s: s.get_freshness_score(), reverse=True)
        
        print(f"      Freshness ranking:")
        for i, script in enumerate(candidates_list[:3], 1):
            print(f"        {i}. '{script.title}' (freshness: {script.get_freshness_score():.2f})")
        
        top_candidates = candidates_list[:3] if len(candidates_list) >= 3 else candidates_list
        selected = random.choice(top_candidates)
        
        print(f"      Randomly selected from top {len(top_candidates)} fresh scripts")
        return selected
    
    def find_fallback_script_for_training_type(self, training_type, goal, max_remaining_duration):
        """Find any suitable script when primary category options fail - EXCLUDES special categories"""
        print(f"🔄 FALLBACK SEARCH: Looking for ANY {training_type} script (excluding special categories)...")
        
        # Get special category names to exclude
        special_categories = self.get_special_category_names(training_type)
        print(f"   Excluding special categories: {special_categories}")
        
        # Find regular exercise categories only
        regular_categories = ScriptCategory.objects.filter(
            training_type=training_type,
            is_active=True
        ).exclude(name__in=special_categories)
        
        print(f"   Searching in {regular_categories.count()} regular exercise categories...")
        
        # Show which categories we're checking
        for category in regular_categories:
            script_count = WorkoutScript.objects.filter(
                type=training_type,
                script_category=category,
                is_active=True
            ).exclude(id__in=self.used_script_ids).count()
            print(f"     • {category.display_name}: {script_count} scripts")
        
        candidates = WorkoutScript.objects.filter(
            type=training_type,
            script_category__in=regular_categories,  # Only regular categories
            goal__in=[goal, 'allround'],
            duration_minutes__lte=max_remaining_duration,
            is_active=True
        ).exclude(id__in=self.used_script_ids)
        
        print(f"   Found {candidates.count()} regular exercise fallback candidates")
        
        if candidates.exists():
            selected = random.choice(candidates)
            print(f"   ✅ Regular fallback selected: '{selected.title}' from {selected.script_category.display_name}")
            return selected
        
        print(f"   ❌ No regular exercise fallback scripts available")
        return None
    
    def get_special_category_names(self, training_type):
        """Get list of special category names to exclude from fallback"""
        special_patterns = {
            'kickboxing': ['surprise', 'kb_surprise'],
            'power_yoga': ['vinyasa', 'py_vinyasa'],
            'calisthenics': ['max', 'challenge', 'cal_max']
        }
        
        patterns = special_patterns.get(training_type, [])
        special_names = []
        
        # Find categories matching special patterns
        all_categories = ScriptCategory.objects.filter(
            training_type=training_type,
            is_active=True
        )
        
        for category in all_categories:
            for pattern in patterns:
                if pattern.lower() in category.name.lower():
                    special_names.append(category.name)
                    break
        
        return special_names
    
    def apply_duration_management(self, enhanced_scripts, training_type, goal):
        """Apply duration management: add filler content or trim if needed"""
        total_duration = sum(script.duration_minutes for script in enhanced_scripts)
        min_duration = self.target_duration - self.time_flexibility
        max_duration = self.target_duration + self.time_flexibility
        
        print(f"\n⏰ DURATION MANAGEMENT")
        print(f"Current: {total_duration:.1f}min | Target: {min_duration:.1f}-{max_duration:.1f}min")
        
        if total_duration < min_duration:
            needed = min_duration - total_duration
            print(f"📈 Workout too short by {needed:.1f}min - adding filler content...")
            self.add_filler_content_to_workout(enhanced_scripts, training_type, goal, needed)
            
        elif total_duration > max_duration:
            excess = total_duration - max_duration
            print(f"📉 Workout too long by {excess:.1f}min - trimming content...")
            enhanced_scripts = self.trim_workout_to_target_duration(enhanced_scripts, max_duration)
        else:
            print(f"✅ Duration within target range")
        
        return enhanced_scripts
    
    def add_filler_content_to_workout(self, selected_scripts, training_type, goal, needed_duration):
        """Add additional content if workout is shorter than target duration - EXCLUDES special categories"""
        print(f"🔍 Looking for filler content ({needed_duration:.1f}min needed)...")
        
        # Get special category names to exclude
        special_categories = self.get_special_category_names(training_type)
        
        # Find regular exercise categories only for filler
        regular_categories = ScriptCategory.objects.filter(
            training_type=training_type,
            is_active=True
        ).exclude(name__in=special_categories)
        
        filler_candidates = WorkoutScript.objects.filter(
            type=training_type,
            script_category__in=regular_categories,  # Only regular categories
            goal__in=[goal, 'allround'],
            duration_minutes__lte=needed_duration,
            is_active=True
        ).exclude(id__in=self.used_script_ids).order_by('duration_minutes')
        
        print(f"Found {filler_candidates.count()} potential regular exercise filler scripts")
        
        added_count = 0
        for candidate in filler_candidates:
            if candidate.duration_minutes <= needed_duration:
                selected_scripts.append(candidate)
                needed_duration -= candidate.duration_minutes
                self.used_script_ids.add(candidate.id)
                candidate.mark_selected()
                added_count += 1
                
                print(f"  ✅ Added filler: '{candidate.title}' ({candidate.duration_minutes}min)")
                
                if needed_duration <= 1.0:
                    break
        
        print(f"📈 Added {added_count} filler scripts, {needed_duration:.1f}min still needed")
    
    def trim_workout_to_target_duration(self, scripts, max_duration):
        """Remove optional content if workout is too long"""
        current_duration = sum(script.duration_minutes for script in scripts)
        
        if current_duration <= max_duration:
            return scripts
        
        print(f"✂️ Trimming workout from {current_duration:.1f}min to ≤{max_duration:.1f}min")
        
        essential_scripts = []
        optional_scripts = []
        
        for script in scripts:
            if (script.is_surprise_round() or 
                script.is_max_challenge() or 
                script.is_vinyasa_transition() or
                self.is_essential_exercise_script(script)):
                essential_scripts.append(script)
                print(f"  🔒 Essential: {script.title}")
            else:
                optional_scripts.append(script)
                print(f"  📋 Optional: {script.title}")
        
        trimmed_scripts = essential_scripts[:]
        current_duration = sum(script.duration_minutes for script in trimmed_scripts)
        
        added_back = 0
        for optional_script in optional_scripts:
            if current_duration + optional_script.duration_minutes <= max_duration:
                trimmed_scripts.append(optional_script)
                current_duration += optional_script.duration_minutes
                added_back += 1
                print(f"  ✅ Kept optional: {optional_script.title}")
        
        print(f"✂️ Trimming complete: kept {len(essential_scripts)} essential + {added_back} optional scripts")
        
        return self.reorder_scripts_logically_for_sport(trimmed_scripts)
    
    def is_essential_exercise_script(self, script):
        """Determine if a script is essential and should not be trimmed"""
        category_name = script.script_category.name.lower()
        essential_patterns = [
            'warmup', 'warm-up', 'cooldown', 'cool-down', 
            'stretch', 'savasana', 'mindfulness', 'connecting'
        ]
        return any(pattern in category_name for pattern in essential_patterns)
    
    def reorder_scripts_logically_for_sport(self, scripts):
        """Reorder scripts in logical sequence after trimming"""
        if not scripts:
            return scripts
            
        warmup_scripts = []
        main_scripts = []
        cooldown_scripts = []
        
        for script in scripts:
            if self.is_warmup_script(script):
                warmup_scripts.append(script)
            elif self.is_cooldown_script(script):
                cooldown_scripts.append(script)
            else:
                main_scripts.append(script)
        
        training_type = scripts[0].type
        if training_type == 'calisthenics':
            main_scripts = self.apply_logical_exercise_ordering(main_scripts)
        
        return warmup_scripts + main_scripts + cooldown_scripts
    
    def is_warmup_script(self, script):
        """Check if script is a warmup script"""
        category_name = script.script_category.name.lower()
        warmup_patterns = ['warmup', 'warm-up', 'connecting', 'sun_greeting']
        return any(pattern in category_name for pattern in warmup_patterns)
    
    def is_cooldown_script(self, script):
        """Check if script is a cooldown script"""
        category_name = script.script_category.name.lower()
        cooldown_patterns = ['cooldown', 'cool-down', 'stretch', 'relax', 'savasana', 'mindfulness']
        return any(pattern in category_name for pattern in cooldown_patterns)
    
    def create_workout_session_record(self, final_scripts, training_type, goal):
        """Create workout session record with metadata and script compilation"""
        total_duration = sum(script.duration_minutes for script in final_scripts)
        
        workout_session = WorkoutSession.objects.create(
            training_type=training_type,
            title=self.generate_descriptive_workout_title(training_type, goal, self.target_duration),
            total_duration=total_duration,
            target_duration=self.target_duration,
            time_flexibility=self.time_flexibility,
            goal=goal,
            compiled_script=self.compile_final_workout_script(final_scripts, training_type),
            sport_additions_applied=self.get_sport_additions_summary()
        )
        
        for i, script in enumerate(final_scripts):
            SessionScript.objects.create(
                workout_session=workout_session,
                workout_script=script,
                sequence_order=i + 1,
                is_sport_addition=(script.is_surprise_round() or 
                                 script.is_max_challenge() or 
                                 script.is_vinyasa_transition())
            )
        
        return workout_session
    
    def compile_final_workout_script(self, scripts, training_type):
        """Compile scripts with Foxing Fit branding, round numbers, and intelligent quote replacement"""
        script_parts = []
        quote_processor = QuoteProcessor()
        round_counter = 1
        
        opening_text = FoxingFitBranding.get_opening_text(training_type)
        script_parts.append(f"{opening_text}\n")
        
        for i, script in enumerate(scripts):
            if self.should_script_have_round_number(script):
                round_header = FoxingFitBranding.format_round_header(
                    round_counter, 
                    script.title, 
                    'nl'
                )
                script_parts.append(f"\n{round_header}\n\n")
                round_counter += 1
            else:
                special_type = FoxingFitBranding.detect_special_round_type(script)
                if special_type:
                    special_header = FoxingFitBranding.format_special_round_header(
                        special_type, 
                        script.title
                    )
                    script_parts.append(f"\n{special_header}\n\n")
                else:
                    script_parts.append(f"\n## {script.script_category.display_name}\n\n")
            
            processed_content = quote_processor.process_script_content(script, training_type)
            script_parts.append(processed_content)
            script_parts.append("\n\n[pause strong] [pause strong]\n")
        
        closing_text = FoxingFitBranding.get_closing_text(training_type)
        script_parts.append(f"\n{closing_text}")
        
        return ''.join(script_parts)
    
    def should_script_have_round_number(self, script):
        """Determine if a script should get a round number in orange text"""
        return FoxingFitBranding.should_use_round_numbering(script.script_category.name)
    
    def get_sport_additions_summary(self):
        """Create summary of sport-specific additions made during generation"""
        summary = {
            'surprise_rounds_added': self.sport_additions.get('surprise_rounds_added', 0),
            'vinyasa_transitions_added': self.sport_additions.get('vinyasa_transitions_added', 0),
            'difficulty_reordered': self.sport_additions.get('difficulty_reordered', 0) > 0,
            'max_challenge_moved_last': self.sport_additions.get('max_challenge_moved_last', 0) > 0
        }
        return summary
    
    def generate_descriptive_workout_title(self, training_type, goal, target_duration):
        """Generate descriptive title for the workout session including duration"""
        type_names = dict(WorkoutScript.TRAINING_TYPES)
        goal_names = dict(WorkoutScript.GOALS)
        
        base_name = type_names.get(training_type, training_type)
        goal_name = goal_names.get(goal, goal)
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        duration_str = f" ({int(target_duration)}min)"
        
        return f"{base_name} - {goal_name}{duration_str} - {timestamp}"
    
    def compile_generation_results(self, workout_session, final_scripts, training_type):
        """Enhanced results with missing content warnings"""
        
        result = {
            'workout_session_id': workout_session.id,
            'title': workout_session.title,
            'training_type': training_type,
            'goal': workout_session.goal,
            'total_duration': workout_session.total_duration,
            'target_duration': self.target_duration,
            'time_status': workout_session.get_time_status(),
            'scripts': [
                {
                    'title': script.title,
                    'script_category': script.script_category.display_name,
                    'duration': script.duration_minutes,
                    'is_sport_addition': (script.is_surprise_round() or 
                                        script.is_max_challenge() or 
                                        script.is_vinyasa_transition())
                }
                for script in final_scripts
            ],
            'compiled_script': workout_session.compiled_script,
            'sport_specific_additions': self.get_sport_additions_summary()
        }
        
        # Add missing content warnings to API response
        if self.missing_categories:
            result['content_warnings'] = {
                'missing_categories': self.missing_categories,
                'substitutions_made': self.fallback_substitutions,
                'message': f"Workout generated with {len(self.fallback_substitutions)} substitutions. Add scripts to missing categories for better results."
            }
        
        return result

    def generate_1hour_workout(self, training_type, goal='allround'):
        """Generate 1-hour workout (backward compatibility)"""
        return self.generate_workout_with_custom_duration(training_type, goal, 60.0)
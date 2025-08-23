# scripts/management/commands/setup.py - UPDATED FOR 3 GOALS

import os
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import WorkoutScript, MotivationalQuote, ScriptCategory, WorkoutTemplate

class Command(BaseCommand):
    help = 'Setup Johnny\'s complete workout system (default: full setup)'
    
    def add_arguments(self, parser):
        # Default behavior: run full setup when no arguments provided
        parser.add_argument('--templates-only', action='store_true',
                          help='Only setup workout templates')
        parser.add_argument('--categories-only', action='store_true', 
                          help='Only setup workout categories')
        parser.add_argument('--dry-run', action='store_true',
                          help='Preview without making changes')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be saved"))
        
        try:
            with transaction.atomic():
                # Default: Run full setup unless specific options provided
                if options['templates_only']:
                    self._setup_johnny_workout_templates(dry_run)
                elif options['categories_only']:
                    self._create_regular_categories(dry_run)
                else:
                    # FULL SETUP (default behavior)
                    self._setup_complete_system(dry_run)
                
                if dry_run:
                    raise Exception("Dry run - rolling back")
                    
        except Exception as e:
            if "Dry run" in str(e):
                self.stdout.write(self.style.SUCCESS("✅ Dry run completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
    
    def _setup_complete_system(self, dry_run):
        """Complete system setup - default behavior"""
        
        self.stdout.write(self.style.SUCCESS("🎯 SETTING UP JOHNNY'S COMPLETE WORKOUT SYSTEM"))
        self.stdout.write("✅ System categories already created via migration")
        
        # Verify system categories exist
        if not dry_run:
            system_categories = ScriptCategory.objects.filter(is_system_category=True)
            if system_categories.count() < 4:
                self.stdout.write(self.style.ERROR("❌ System categories missing! Please run: python manage.py migrate"))
                return
            
            self.stdout.write(f"🔒 Found {system_categories.count()} system categories:")
            for cat in system_categories:
                self.stdout.write(f"   ✅ {cat.name} → {cat.display_name} ({cat.training_type})")
        
        # STEP 1: Create regular categories
        self._create_regular_categories(dry_run)
        
        # STEP 2: Create improved templates
        self._setup_johnny_workout_templates(dry_run)
        
        # STEP 3: Show system summary
        if not dry_run:
            self._show_system_summary()
    
    def _create_regular_categories(self, dry_run):
        """Create regular workout categories for 3-goal system"""
        
        self.stdout.write("\n📁 CREATING REGULAR CATEGORIES (3-Goal System)")
        self.stdout.write("=" * 55)
        
        # KICKBOXING: Based on actual Drive folders
        kickboxing_categories = [
            ('kb_warmup', 'Warmup'),
            ('kb_cooldown', 'Cooldown / Shadow Boxing'),
            ('kb_footwork', 'Footwork'),
            ('kb_combinations', 'Combinations'),
            ('kb_legs_kicks', 'Legs & Kicks'),
            ('kb_abs', 'Abs Round'),
            ('kb_defence', 'Defence'),
            ('kb_stretch_relax', 'Stretch and Relax'),
            ('kb_reaction_time', 'Reaction Time'),  # NEW: Added missing category
            # kb_surprise already created as system category
        ]
        
        # POWER YOGA: Improved logical flow
        power_yoga_categories = [
            ('py_connecting', 'Connecting Phase'),
            ('py_sun_greeting', 'Sun Greeting'),
            ('py_standing', 'Standing Poses'),
            ('py_yoga_flow', 'Yoga Flow'),
            ('py_seated', 'Seated Poses'),
            ('py_lying', 'Lying Poses'),
            ('py_savasana', 'Savasana'),
            ('py_mindfulness', 'Mindfulness'),
            # py_vinyasa_s2s and py_vinyasa_s2sit already created as system categories
        ]
        
        # CALISTHENICS: Complete set
        calisthenics_categories = [
            ('cal_warmup', 'Warmup'),
            ('cal_pushup', 'Push-up Variations'),
            ('cal_situp', 'Sit-up Variations'),
            ('cal_pullup', 'Pull-up Variations'),
            ('cal_dips', 'Dips Variations'),
            ('cal_lsit', 'L-sit Variations'),
            ('cal_explosive', 'Explosive Moves'),
            ('cal_handstand', 'Handstand Variations'),
            ('cal_back_lever', 'Back-lever Variations'),
            ('cal_front_lever', 'Front-lever Variations'),
            ('cal_planche', 'Planche Variations'),
            ('cal_static_holds', 'Static Holds'),
            # cal_max_challenge already created as system category
        ]
        
        all_categories = [
            ('kickboxing', kickboxing_categories),
            ('power_yoga', power_yoga_categories),
            ('calisthenics', calisthenics_categories)
        ]
        
        created_count = 0
        
        for training_type, categories in all_categories:
            self.stdout.write(f"\n🎯 Creating {training_type} categories...")
            
            for name, display_name in categories:
                if not dry_run:
                    category, created = ScriptCategory.objects.get_or_create(
                        training_type=training_type,
                        name=name,
                        defaults={
                            'display_name': display_name,
                            'description': f'Based on Johnny\'s {training_type} methodology',
                            'is_system_category': False,
                            'is_active': True
                        }
                    )
                    if created:
                        created_count += 1
                        self.stdout.write(f"   ✅ Created: {display_name}")
                    else:
                        self.stdout.write(f"   ⏭️ Exists: {display_name}")
                else:
                    created_count += 1
                    self.stdout.write(f"   [DRY RUN] {display_name}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {created_count} regular categories"))
    
    def _setup_johnny_workout_templates(self, dry_run):
        """Create improved workout templates for 3-goal system"""
        
        self.stdout.write(self.style.SUCCESS("\n🏗️ CREATING IMPROVED WORKOUT TEMPLATES"))
        self.stdout.write("✅ Optimized for 3-goal system (allround, strength, flexibility)")
        
        def get_category(training_type, name):
            if dry_run:
                return type('MockCategory', (), {'id': 1, 'name': name, 'display_name': name})()
            return ScriptCategory.objects.get(training_type=training_type, name=name)
        
        # IMPROVED KICKBOXING TEMPLATES
        self.stdout.write(f"\n🥊 KICKBOXING TEMPLATES (Improved)")
        kickboxing_templates = [
            (1, 'kb_warmup', ['kb_cooldown'], True, False, "Start: Warmup OR Shadow Boxing"),
            (2, 'kb_combinations', [], True, True, "Core: Combinations + AUTO-SURPRISE"),
            (3, 'kb_legs_kicks', ['kb_abs'], True, True, "Power: Legs/Kicks OR Abs + AUTO-SURPRISE"), 
            (4, 'kb_reaction_time', ['kb_footwork', 'kb_defence'], False, False, "Optional: Reaction Time OR Footwork OR Defence"),
            (5, 'kb_stretch_relax', [], True, False, "End: Stretch and Relax"),
        ]
        
        # IMPROVED POWER YOGA TEMPLATES (Logical Flow)
        self.stdout.write(f"\n🧘‍♀️ POWER YOGA TEMPLATES (Improved Logical Flow)")
        power_yoga_templates = [
            (1, 'py_connecting', [], True, False, None, "Opening: Breath connection"),
            (2, 'py_sun_greeting', [], True, False, None, "Warmup: Sun salutations"),
            (3, 'py_standing', [], True, False, None, "Standing poses sequence 1"),
            (4, 'py_yoga_flow', ['py_standing'], False, False, None, "Flow OR More standing poses"),
            (5, 'py_standing', [], False, True, 'standing_to_sitting', "Final standing + S→Sit transition"),
            (6, 'py_seated', [], True, False, None, "Seated poses"),
            (7, 'py_lying', [], True, False, None, "Lying poses"),
            (8, 'py_savasana', ['py_mindfulness'], True, False, None, "End: Savasana OR Mindfulness"),
        ]
        
        # IMPROVED CALISTHENICS TEMPLATES
        self.stdout.write(f"\n💪 CALISTHENICS TEMPLATES (Improved)")
        calisthenics_templates = [
            (1, 'cal_warmup', [], True, False, "Start: Joint mobility"),
            (2, 'cal_pushup', ['cal_situp'], True, False, "Basic: Push-ups OR Sit-ups"),
            (3, 'cal_pullup', ['cal_dips'], True, False, "Strength: Pull-ups OR Dips"),
            (4, 'cal_lsit', ['cal_explosive'], False, False, "Intermediate: L-sit OR Explosive"),
            (5, 'cal_handstand', ['cal_back_lever', 'cal_front_lever', 'cal_planche'], False, False, "Advanced: Choose one"),
            (6, 'cal_static_holds', [], False, False, "Conditioning: Static holds"),
            (7, 'cal_max_challenge', [], True, False, "Finale: MAX challenge"),
        ]
        
        created_count = 0
        
        # Create kickboxing templates
        for order, primary_name, alt_names, required, add_surprise, notes in kickboxing_templates:
            primary_category = get_category('kickboxing', primary_name)
            
            if not dry_run:
                template, created = WorkoutTemplate.objects.get_or_create(
                    training_type='kickboxing',
                    sequence_order=order,
                    defaults={
                        'primary_category': primary_category,
                        'is_required': required,
                        'add_surprise_round_after': add_surprise,
                        'is_active': True,
                    }
                )
                
                # Add alternatives
                template.alternative_categories.clear()
                for alt_name in alt_names:
                    alt_category = get_category('kickboxing', alt_name)
                    template.alternative_categories.add(alt_category)
                
                if created:
                    created_count += 1
                    self.stdout.write(f"   ✅ Step {order}: {notes}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {notes} (exists)")
            else:
                created_count += 1
                self.stdout.write(f"   [DRY RUN] Step {order}: {notes}")
        
        # Create power yoga templates
        for order, primary_name, alt_names, required, add_vinyasa, vinyasa_type, notes in power_yoga_templates:
            primary_category = get_category('power_yoga', primary_name)
            
            if not dry_run:
                template, created = WorkoutTemplate.objects.get_or_create(
                    training_type='power_yoga',
                    sequence_order=order,
                    defaults={
                        'primary_category': primary_category,
                        'is_required': required,
                        'add_vinyasa_transition_after': add_vinyasa,
                        'vinyasa_type': vinyasa_type,
                        'is_active': True,
                    }
                )
                
                # Add alternatives
                template.alternative_categories.clear()
                for alt_name in alt_names:
                    alt_category = get_category('power_yoga', alt_name)
                    template.alternative_categories.add(alt_category)
                
                if created:
                    created_count += 1
                    self.stdout.write(f"   ✅ Step {order}: {notes}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {notes} (exists)")
            else:
                created_count += 1
                self.stdout.write(f"   [DRY RUN] Step {order}: {notes}")
        
        # Create calisthenics templates
        for order, primary_name, alt_names, required, add_max, notes in calisthenics_templates:
            primary_category = get_category('calisthenics', primary_name)
            
            if not dry_run:
                template, created = WorkoutTemplate.objects.get_or_create(
                    training_type='calisthenics',
                    sequence_order=order,
                    defaults={
                        'primary_category': primary_category,
                        'is_required': required,
                        'add_max_challenge_after': add_max,
                        'is_active': True,
                    }
                )
                
                # Add alternatives
                template.alternative_categories.clear()
                for alt_name in alt_names:
                    alt_category = get_category('calisthenics', alt_name)
                    template.alternative_categories.add(alt_category)
                
                if created:
                    created_count += 1
                    self.stdout.write(f"   ✅ Step {order}: {notes}")
                else:
                    self.stdout.write(f"   ⏭️ Step {order}: {notes} (exists)")
            else:
                created_count += 1
                self.stdout.write(f"   [DRY RUN] Step {order}: {notes}")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Created {created_count} improved templates"))
    
    def _show_system_summary(self):
        """Show summary of complete system setup"""
        self.stdout.write(self.style.SUCCESS("\n🎯 JOHNNY'S WORKOUT SYSTEM READY"))
        
        self.stdout.write("\n🏆 Johnny's Sport Methodologies:")
        self.stdout.write("   🥊 Kickboxing: Surprise rounds after core training")
        self.stdout.write("   🧘‍♀️ Power Yoga: Logical S→Sit transition between standing and seated")  
        self.stdout.write("   💪 Calisthenics: Difficulty progression with MAX challenge finale")
        
        self.stdout.write("\n🎯 3-Goal System:")
        self.stdout.write("   📊 allround: General fitness and balance")
        self.stdout.write("   💪 strength: Power, muscle building, intense training")
        self.stdout.write("   🤸 flexibility: Stretching, mobility, relaxation")
        
        self.stdout.write("\n🔒 System Categories (Auto-Protected):")
        self.stdout.write("   🎯 kb_surprise - Kickboxing surprise rounds")
        self.stdout.write("   💪 cal_max_challenge - Calisthenics MAX challenge")
        self.stdout.write("   🌊 py_vinyasa_s2sit - Power Yoga standing-to-sitting transitions")
        
        self.stdout.write("\n🚀 Next Steps:")
        self.stdout.write("   1. Import scripts: python manage.py import_scripts --folder-path DATABASE_CONTENT")
        self.stdout.write("   2. Import quotes: python manage.py import_quotes --folder-path DATABASE_CONTENT")
        self.stdout.write("   3. Generate workouts: API endpoints ready")
        
        self.stdout.write("\n💡 Usage:")
        self.stdout.write("   python manage.py setup                    # Full setup (default)")
        self.stdout.write("   python manage.py setup --templates-only   # Only templates")
        self.stdout.write("   python manage.py setup --categories-only  # Only categories")
        self.stdout.write("   python manage.py setup --dry-run          # Preview changes")
import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from scripts.models import WorkoutScript, ScriptCategory

# For DOCX file reading
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

class Command(BaseCommand):
    help = 'Import Johnny\'s workout scripts from DATABASE_CONTENT folder (3-goal system)'
    
    def add_arguments(self, parser):
        parser.add_argument('--folder-path', type=str, default='DATABASE_CONTENT',
                          help='Path to content folder (default: DATABASE_CONTENT)')
        parser.add_argument('--dry-run', action='store_true', 
                          help='Preview without making changes')
        parser.add_argument('--update-existing', action='store_true',
                          help='Update existing scripts if found')
        parser.add_argument('--install-docx', action='store_true',
                          help='Show instructions to install python-docx')
    
    def handle(self, *args, **options):
        # Check if python-docx is available
        if options['install_docx']:
            self._show_docx_installation_instructions()
            return
            
        if not DOCX_AVAILABLE:
            self.stdout.write(self.style.ERROR("❌ python-docx not installed!"))
            self.stdout.write("Run: python manage.py import_scripts --install-docx")
            return
        
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be saved"))
        
        try:
            with transaction.atomic():
                self._import_from_local_folder(
                    options['folder_path'], 
                    dry_run, 
                    options['update_existing']
                )
                
                if dry_run:
                    raise Exception("Dry run - rolling back")
                    
        except Exception as e:
            if "Dry run" in str(e):
                self.stdout.write(self.style.SUCCESS("✅ Dry run completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
    
    def _show_docx_installation_instructions(self):
        """Show installation instructions for python-docx"""
        self.stdout.write(self.style.SUCCESS("📋 DOCX SUPPORT INSTALLATION"))
        self.stdout.write("")
        self.stdout.write("To read DOCX files, install python-docx:")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("pip install python-docx"))
        self.stdout.write("")
        self.stdout.write("Or if using pipenv:")
        self.stdout.write(self.style.SUCCESS("pipenv install python-docx"))
        self.stdout.write("")
        self.stdout.write("Or add to requirements.txt:")
        self.stdout.write("python-docx==0.8.11")
    
    def _import_from_local_folder(self, folder_path, dry_run, update_existing):
        """Import workout scripts with improved folder mapping for 3-goal system"""
        
        if not os.path.exists(folder_path):
            self.stdout.write(self.style.ERROR(f"❌ Folder {folder_path} does not exist"))
            self._show_folder_structure_example(folder_path)
            return
        
        # IMPROVED folder category mapping for 3-goal system
        folder_category_mapping = {
            # KICKBOXING MAPPINGS (improved warmup detection)
            'warmup': 'kb_warmup',
            'warm-up': 'kb_warmup',
            'warm up': 'kb_warmup',           # NEW: Handle "Warm up" folder
            'warm - up': 'kb_warmup',         # NEW: Handle "Warm - up" folder (with spaces/dash)
            'combinations': 'kb_combinations',
            'combinations (empty)': 'kb_combinations',
            'combo': 'kb_combinations',
            'combos': 'kb_combinations',
            'legs & kicks': 'kb_legs_kicks',
            'legs & kicks ': 'kb_legs_kicks',
            'legs and kicks': 'kb_legs_kicks',
            'legs': 'kb_legs_kicks',
            'kicks': 'kb_legs_kicks',
            'abs round': 'kb_abs',
            'abs': 'kb_abs',
            'footwork': 'kb_footwork',
            'footwork (empty)': 'kb_footwork',
            'defence': 'kb_defence',
            'defence (empty)': 'kb_defence',
            'defense': 'kb_defence',
            'reaction time': 'kb_reaction_time',     # NEW: Added missing folder
            'reaction': 'kb_reaction_time',
            'surprise rounds': 'kb_surprise',        # System category
            'suprise rounds': 'kb_surprise',         # Handle typo
            'surprise': 'kb_surprise',
            'cooldown': 'kb_cooldown',
            'cooldown (empty)': 'kb_cooldown',
            'cool-down': 'kb_cooldown',
            'cool down': 'kb_cooldown',
            'stretch and relax': 'kb_stretch_relax',
            'stretch': 'kb_stretch_relax',
            'relax': 'kb_stretch_relax',
            'stretching': 'kb_stretch_relax',
            
            # POWER YOGA MAPPINGS
            'connecting phase': 'py_connecting',
            'connecting': 'py_connecting',
            'sun greeting': 'py_sun_greeting',
            'sun salutation': 'py_sun_greeting',
            'sun': 'py_sun_greeting',
            'standing poses': 'py_standing',
            'standing': 'py_standing',
            'yoga flow': 'py_yoga_flow',
            'flow': 'py_yoga_flow',
            'seated poses': 'py_seated',
            'seated': 'py_seated',
            'sitting poses': 'py_seated',
            'sitting': 'py_seated',
            'lying poses': 'py_lying',
            'lying': 'py_lying',
            'savasana': 'py_savasana',
            'mindfulness': 'py_mindfulness',
            'mindfullness': 'py_mindfulness',        # Handle typo
            # System vinyasa categories
            'vinyasa standing-to-standing': 'py_vinyasa_s2s',
            'vinyasa standing to standing': 'py_vinyasa_s2s',
            'vinyasa s2s': 'py_vinyasa_s2s',
            'vinyasa standing-to-sitting': 'py_vinyasa_s2sit',
            'vinyasa standing to sitting': 'py_vinyasa_s2sit',
            'vinyasa s2sit': 'py_vinyasa_s2sit',
            
            # CALISTHENICS MAPPINGS (improved warmup detection)
            'warmup': 'cal_warmup',
            'warm-up': 'cal_warmup',
            'warm up': 'cal_warmup',             # NEW: Handle "Warm up" folder
            'warm - up': 'cal_warmup',           # NEW: Handle "Warm - up" folder
            'push-up variation': 'cal_pushup',
            'pushup variation': 'cal_pushup',
            'push-up': 'cal_pushup',
            'pushup': 'cal_pushup',
            'push up': 'cal_pushup',
            'pushups': 'cal_pushup',
            'push-ups': 'cal_pushup',
            'sit-up variation': 'cal_situp',
            'situp variation': 'cal_situp',
            'sit-up': 'cal_situp',
            'situp': 'cal_situp',
            'sit up': 'cal_situp',
            'situps': 'cal_situp',
            'sit-ups': 'cal_situp',
            'pull-up variation': 'cal_pullup',
            'pullup variation': 'cal_pullup',
            'pull-up': 'cal_pullup',
            'pullup': 'cal_pullup',
            'pull up': 'cal_pullup',
            'pullups': 'cal_pullup',
            'pull-ups': 'cal_pullup',
            'dips variation': 'cal_dips',
            'dips': 'cal_dips',
            'dip': 'cal_dips',
            'l-sit variation': 'cal_lsit',
            'l-sit': 'cal_lsit',
            'lsit': 'cal_lsit',
            'l sit': 'cal_lsit',
            'explosive moves': 'cal_explosive',
            'explosive': 'cal_explosive',
            'handstand variation': 'cal_handstand',
            'handstand variation (empty)': 'cal_handstand',
            'handstand': 'cal_handstand',
            'back-lever variation': 'cal_back_lever',
            'back-lever': 'cal_back_lever',
            'back lever': 'cal_back_lever',
            'front-lever variation': 'cal_front_lever',
            'front-lever': 'cal_front_lever',
            'front lever': 'cal_front_lever',
            'planche variation': 'cal_planche',
            'planche': 'cal_planche',
            'static holds': 'cal_static_holds',
            'static holds (empty)': 'cal_static_holds',
            'static': 'cal_static_holds',
            'holds': 'cal_static_holds',
            # System MAX challenge category
            'max challenge': 'cal_max_challenge',
            'max': 'cal_max_challenge',
            'challenge': 'cal_max_challenge',
            
            # Skip quotes folders
            'quotes': None,
            'remember quotes': None,
        }
        
        # Walk through the folder structure
        total_imported = 0
        total_updated = 0
        total_skipped = 0
        special_rounds_found = 0
        errors = []
        
        for sport_folder in os.listdir(folder_path):
            sport_path = os.path.join(folder_path, sport_folder)
            
            if not os.path.isdir(sport_path):
                continue
                
            # Map sport folder to training type
            sport_type = self._map_sport_folder_to_type(sport_folder)
            if not sport_type:
                self.stdout.write(self.style.WARNING(f"⚠️ Unknown sport folder: {sport_folder}"))
                continue
            
            self.stdout.write(f"\n📁 Processing {sport_folder} ({sport_type})...")
            
            # Process each category folder within sport
            sport_file_count = 0
            for category_folder in os.listdir(sport_path):
                category_path = os.path.join(sport_path, category_folder)
                
                if not os.path.isdir(category_path):
                    continue
                
                # Map folder name to category (improved mapping)
                category_name = self._map_folder_to_category(category_folder, folder_category_mapping, sport_type)
                if not category_name:
                    self.stdout.write(f"   ⚠️ Skipping unknown/quotes category: {category_folder}")
                    continue
                
                # Check if this is a special round category
                is_special = self._is_special_round_category(category_name)
                special_indicator = self._get_special_round_indicator(category_name)
                
                self.stdout.write(f"   📂 Processing category: {category_folder} -> {category_name} {special_indicator}")
                
                # Process files in this category
                category_file_count = 0
                files_in_category = []
                
                try:
                    files_in_category = [f for f in os.listdir(category_path) 
                                       if f.lower().endswith(('.docx', '.txt'))]
                except PermissionError:
                    self.stdout.write(f"   ❌ Permission denied accessing: {category_path}")
                    continue
                
                if not files_in_category:
                    self.stdout.write(f"   📁 Empty category: {category_folder} (no .docx/.txt files)")
                    continue
                
                self.stdout.write(f"   📄 Found {len(files_in_category)} files in {category_folder}")
                
                for file_name in files_in_category:
                    file_path = os.path.join(category_path, file_name)
                    
                    try:
                        result = self._import_single_file(
                            file_path, file_name, sport_type, category_name, dry_run, update_existing
                        )
                        if result == 'created':
                            category_file_count += 1
                            total_imported += 1
                            if is_special:
                                special_rounds_found += 1
                        elif result == 'updated':
                            category_file_count += 1
                            total_updated += 1
                        elif result == 'skipped':
                            total_skipped += 1
                    except Exception as e:
                        error_msg = f"Error importing {file_path}: {str(e)}"
                        errors.append(error_msg)
                        self.stdout.write(self.style.ERROR(f"   ❌ {error_msg}"))
                
                if category_file_count > 0:
                    self.stdout.write(f"   ✅ {category_folder}: {category_file_count} files processed")
                    sport_file_count += category_file_count
                else:
                    self.stdout.write(f"   ⏭️ {category_folder}: No files processed")
            
            if sport_file_count > 0:
                self.stdout.write(f"📊 {sport_folder} total: {sport_file_count} files processed")
        
        # Enhanced summary for 3-goal system
        self.stdout.write(f"\n🎯 IMPORT SUMMARY (3-Goal System):")
        self.stdout.write(self.style.SUCCESS(f"✅ New files imported: {total_imported}"))
        self.stdout.write(self.style.SUCCESS(f"🎯 Special rounds found: {special_rounds_found} (surprise, MAX challenge, vinyasa)"))
        if total_updated > 0:
            self.stdout.write(self.style.SUCCESS(f"🔄 Files updated: {total_updated}"))
        if total_skipped > 0:
            self.stdout.write(self.style.WARNING(f"⏭️ Files skipped (already exist): {total_skipped}"))
        if errors:
            self.stdout.write(self.style.WARNING(f"⚠️ Errors encountered: {len(errors)}"))
            for error in errors[:5]:
                self.stdout.write(f"   {error}")
        
        # 3-goal system ready message
        if not dry_run and total_imported > 0:
            self.stdout.write(f"\n🎯 3-GOAL SYSTEM READY:")
            self.stdout.write("✅ Scripts imported and categorized for allround, strength, flexibility goals")
            self.stdout.write("✅ Configure templates at: http://localhost:8000/admin/scripts/workouttemplate/")
            self.stdout.write("✅ Missing folders now handled: 'Warm up', 'Warm - up', 'Reaction time'")
    
    def _show_folder_structure_example(self, folder_path):
        """Show example folder structure with improved folder names"""
        self.stdout.write(f"💡 Create folder structure like:")
        self.stdout.write(f"   {folder_path}/")
        self.stdout.write(f"   ├── Kickboxing/")
        self.stdout.write(f"   │   ├── Warm up/              # NOW SUPPORTED")
        self.stdout.write(f"   │   ├── Combinations/")
        self.stdout.write(f"   │   ├── Reaction time/        # NOW SUPPORTED")
        self.stdout.write(f"   │   └── Suprise Rounds/       # Auto-detected as kb_surprise")
        self.stdout.write(f"   ├── Power Yoga/")
        self.stdout.write(f"   │   ├── Standing Poses/")
        self.stdout.write(f"   │   └── Vinyasa Standing-to-Sitting/")
        self.stdout.write(f"   └── Calisthenics/")
        self.stdout.write(f"       ├── Warm - up/            # NOW SUPPORTED")
        self.stdout.write(f"       ├── Push-up Variation/")
        self.stdout.write(f"       └── MAX Challenge/")
    
    def _map_sport_folder_to_type(self, folder_name):
        """Map folder name to training type"""
        folder_lower = folder_name.lower().strip()
        if 'kickbox' in folder_lower:
            return 'kickboxing'
        elif 'yoga' in folder_lower or 'power' in folder_lower:
            return 'power_yoga'
        elif 'calisthen' in folder_lower:
            return 'calisthenics'
        return None
    
    def _map_folder_to_category(self, folder_name, mapping, sport_type=None):
        """Enhanced folder mapping with better warmup detection"""
        folder_clean = folder_name.lower().strip()
        
        # Direct mapping first (exact match)
        if folder_clean in mapping:
            return mapping[folder_clean]
        
        # Enhanced warmup detection for problematic folder names
        if self._is_warmup_folder(folder_clean):
            if sport_type == 'kickboxing':
                return 'kb_warmup'
            elif sport_type == 'calisthenics':
                return 'cal_warmup'
        
        # Enhanced reaction time detection
        if self._is_reaction_time_folder(folder_clean):
            return 'kb_reaction_time'
        
        # Handle variations and partial matches
        for key, value in mapping.items():
            if value is None:  # Skip None values (quotes folders)
                continue
            if key in folder_clean or folder_clean in key:
                return value
        
        # Smart fallback with enhanced special round detection
        return self._infer_category_from_folder_name(folder_clean, sport_type)
    
    def _is_warmup_folder(self, folder_name):
        """Enhanced warmup folder detection"""
        warmup_patterns = [
            'warmup', 'warm-up', 'warm up', 'warm - up',
            'warmup (empty)', 'warm-up (empty)', 'warm up (empty)'
        ]
        return folder_name in warmup_patterns or any(pattern in folder_name for pattern in ['warm up', 'warm-up', 'warmup'])
    
    def _is_reaction_time_folder(self, folder_name):
        """Detect reaction time folders"""
        reaction_patterns = ['reaction time', 'reaction', 'reaction time (empty)']
        return folder_name in reaction_patterns or 'reaction' in folder_name
    
    def _infer_category_from_folder_name(self, folder_name, sport_type=None):
        """Enhanced category inference with special round detection"""
        folder_lower = folder_name.lower()
        
        # SPECIAL ROUND DETECTION
        if any(word in folder_lower for word in ['surprise', 'suprise']):
            return 'kb_surprise'
        elif 'max' in folder_lower and 'challenge' in folder_lower:
            return 'cal_max_challenge'
        elif 'vinyasa' in folder_lower:
            if 's2s' in folder_lower or ('standing' in folder_lower and 'standing' in folder_lower):
                return 'py_vinyasa_s2s'
            elif 's2sit' in folder_lower or ('standing' in folder_lower and 'sitting' in folder_lower):
                return 'py_vinyasa_s2sit'
            else:
                return 'py_vinyasa_s2s'  # Default vinyasa type
        
        # 🔧 FIXED: Enhanced warmup detection with proper sport mapping
        if self._is_warmup_folder(folder_lower):
            if sport_type == 'kickboxing':
                return 'kb_warmup'
            elif sport_type == 'calisthenics':
                return 'cal_warmup'
            elif sport_type == 'power_yoga':
                return 'py_connecting'  # Power yoga uses connecting phase instead of warmup
            else:
                return None  # Unknown sport type
        
        # Enhanced reaction time detection
        if self._is_reaction_time_folder(folder_lower):
            return 'kb_reaction_time'
        
        return None
    
    def _is_special_round_category(self, category_name):
        """Check if category is a special round"""
        special_categories = ['kb_surprise', 'cal_max_challenge', 'py_vinyasa_s2s', 'py_vinyasa_s2sit']
        return category_name in special_categories
    
    def _get_special_round_indicator(self, category_name):
        """Get visual indicator for special round categories"""
        indicators = {
            'kb_surprise': '🎯 (Admin-controlled surprise rounds)',
            'cal_max_challenge': '💪 (Admin-controlled MAX challenge)',
            'py_vinyasa_s2s': '🌊 (Admin-controlled vinyasa S→S)',
            'py_vinyasa_s2sit': '🌊 (Admin-controlled vinyasa S→Sit)',
        }
        return indicators.get(category_name, '')
    
    def _import_single_file(self, file_path, file_name, sport_type, category_name, dry_run, update_existing):
        """Import a single workout script file for 3-goal system"""
        
        # Extract duration from filename
        duration = self._extract_duration_from_filename(file_name)
        
        # Clean title from filename
        title = self._clean_title_from_filename(file_name)
        
        # Read file content
        content = self._read_file_content(file_path, file_name)
        
        if not content or len(content.strip()) < 10:
            content = self._create_placeholder_content(file_name, duration)
        
        # Determine goal based on category and content (3-goal system)
        goal = self._determine_goal_3_system(category_name, title, content)
        
        if not dry_run:
            # Get script category
            try:
                script_category = ScriptCategory.objects.get(
                    training_type=sport_type,
                    name=category_name
                )
            except ScriptCategory.DoesNotExist:
                raise Exception(f"Category '{category_name}' not found for {sport_type}. Please run: python manage.py setup")
            
            # Check if script already exists
            existing_script = WorkoutScript.objects.filter(
                title=title,
                type=sport_type,
                script_category=script_category
            ).first()
            
            if existing_script:
                if update_existing:
                    existing_script.content = content
                    existing_script.duration_minutes = duration
                    existing_script.goal = goal
                    existing_script.notes = f'Updated from {file_path} for 3-goal system'
                    existing_script.save()
                    return 'updated'
                else:
                    return 'skipped'
            else:
                WorkoutScript.objects.create(
                    title=title,
                    type=sport_type,
                    script_category=script_category,
                    content=content,
                    duration_minutes=duration,
                    goal=goal,
                    language='nl',
                    notes=f'Imported from {file_path} for 3-goal system'
                )
                return 'created'
        else:
            # Dry run output with special round indication
            special_indicator = self._get_special_round_indicator(category_name)
            content_preview = content[:50] + "..." if len(content) > 50 else content
            self.stdout.write(
                f"   [DRY RUN] CREATE: {title} ({duration:.2f}min, {goal}) {special_indicator}"
            )
            return 'created'
    
    def _read_file_content(self, file_path, file_name):
        """Read content from DOCX or TXT file"""
        try:
            if file_path.lower().endswith('.docx'):
                return self._read_docx_content(file_path)
            elif file_path.lower().endswith('.txt'):
                return self._read_txt_content(file_path)
            else:
                return ""
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   ⚠️ Could not read {file_name}: {str(e)}"))
            return ""
    
    def _read_docx_content(self, file_path):
        """Read content from DOCX file using python-docx"""
        try:
            doc = docx.Document(file_path)
            content_parts = []
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    content_parts.append(text)
            
            content = '\n\n'.join(content_parts)
            return self._clean_docx_content(content)
            
        except Exception as e:
            raise Exception(f"Failed to read DOCX file: {str(e)}")
    
    def _read_txt_content(self, file_path):
        """Read content from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            return content
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read().strip()
                return content
            except Exception as e:
                raise Exception(f"Failed to read TXT file: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to read TXT file: {str(e)}")
    
    def _clean_docx_content(self, content):
        """Clean up content extracted from DOCX"""
        if not content:
            return ""
        
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        # Add pause markers if they don't exist
        if '[pause' not in content.lower():
            content = re.sub(r'\.(\s*\n)', '.\n\n[pause weak]\n', content)
            content = re.sub(r'\n\n(?!\[pause)', '\n\n[pause strong]\n\n', content)
        
        return content
    
    def _create_placeholder_content(self, filename, duration):
        """Create placeholder content when file cannot be read"""
        return f"""[FILE: {filename}]
Duration: {duration:.2f} minutes

⚠️ CONTENT COULD NOT BE READ AUTOMATICALLY

📋 TO COMPLETE THIS SCRIPT:
1. Open the original file: {filename}
2. Copy the workout content manually
3. Edit this script in the Django admin
4. Replace this placeholder with the actual workout content
5. Add [pause strong] and [pause weak] markers as needed

This script was automatically imported for the 3-goal system.
"""
    
    def _extract_duration_from_filename(self, filename):
        """Extract duration from filename with improved parsing"""
        name_without_ext = os.path.splitext(filename)[0]
        
        # Pattern 1: (MM_SS) format
        underscore_pattern = r'\((\d{1,2})_(\d{2})\)'
        match = re.search(underscore_pattern, name_without_ext)
        
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            if seconds > 59:
                seconds = 59
            return minutes + (seconds / 60.0)
        
        # Pattern 2: (MM:SS) format
        colon_pattern = r'\((\d{1,2}):(\d{2})\)'
        match = re.search(colon_pattern, name_without_ext)
        
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            if seconds > 59:
                seconds = 59
            return minutes + (seconds / 60.0)
        
        # Default duration based on category
        return self._get_default_duration_for_category(filename, name_without_ext)
    
    def _get_default_duration_for_category(self, filename, clean_name):
        """Get default duration based on category patterns"""
        filename_lower = filename.lower()
        clean_lower = clean_name.lower()
        
        if 'surprise' in clean_lower or 'suprise' in clean_lower:
            return 4.0
        elif 'max' in clean_lower and 'challenge' in clean_lower:
            return 5.0
        elif 'vinyasa' in clean_lower:
            return 3.5
        elif any(word in clean_lower for word in ['warmup', 'warm-up', 'warm up', 'warm - up']):
            return 8.0
        elif any(word in clean_lower for word in ['cooldown', 'stretch', 'relax']):
            return 6.0
        else:
            return 10.0
    
    def _clean_title_from_filename(self, filename):
        """Clean up filename to create a proper title"""
        title = os.path.splitext(filename)[0]
        
        # Remove duration patterns
        title = re.sub(r'\(\d{1,2}_\d{2}\)', '', title)
        title = re.sub(r'\(\d{1,2}:\d{2}\)', '', title)
        title = re.sub(r'\(\d+\s*(seconds?|seconden?|sec)\s*\)', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\(\d+\s*min(?:utes?)?\s*\)', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\(\d{1,4}\)', '', title)
        
        # Remove round prefixes
        title = re.sub(r'^(Round|Ronde)\s*\d+\s*:?\s*', '', title, flags=re.IGNORECASE)
        
        # Clean up formatting
        title = title.replace('_', ' ').replace('-', ' ')
        title = re.sub(r'\.+', '.', title)
        title = title.rstrip('.')
        title = re.sub(r'\s+', ' ', title).strip()
        title = title.title()
        
        return title
    
    def _determine_goal_3_system(self, category_name, title, content):
        """Determine workout goal based on category and content for 3-goal system"""
        
        # Special round categories
        if category_name in ['kb_surprise', 'cal_max_challenge']:
            return 'strength'
        elif 'vinyasa' in category_name:
            return 'flexibility'
        
        # Category-based mapping for 3-goal system
        strength_categories = [
            'cal_pullup', 'cal_pushup', 'cal_dips', 'cal_lsit', 'cal_handstand',
            'cal_back_lever', 'cal_front_lever', 'cal_planche', 'cal_explosive',
            'kb_combinations', 'kb_legs_kicks', 'kb_abs'
        ]
        
        flexibility_categories = [
            'kb_stretch_relax', 'py_savasana', 'py_mindfulness', 'py_lying',
            'py_seated', 'cal_static_holds'
        ]
        
        if category_name in strength_categories:
            return 'strength'
        elif category_name in flexibility_categories:
            return 'flexibility'
        
        # Default to allround for warmup, cooldown, connecting, etc.
        return 'allround'
"""
Management command to import audio workout scripts from mp3 files

This command:
1. Scans mp3 scripts folder organized by sport
2. Extracts audio duration from each MP3
3. Maps audio files to script categories based on filename patterns
4. Creates new WorkoutScript entries with audio files attached
5. Validates and reports on the import process

Usage:
    python manage.py import_audio_scripts --analyze  # Dry run to see what would be imported
    python manage.py import_audio_scripts --import   # Actually import the files
"""

import os
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files import File
from django.db import transaction
from scripts.models import WorkoutScript, ScriptCategory
from generator.audio_validator import AudioValidator


class Command(BaseCommand):
    help = 'Import audio workout scripts from mp3 files folder'
    
    # Mapping of folder names to training types
    FOLDER_TO_TRAINING_TYPE = {
        'Calisthenics': 'calisthenics',
        'kickboksen': 'kickboxing',
        'power yoga': 'power_yoga',
    }
    
    # Category mapping patterns - maps filename keywords to category names
    CATEGORY_PATTERNS = {
        'calisthenics': {
            'back lever': 'cal_back_lever',
            'back-lever': 'cal_back_lever',
            'dips': 'cal_dips',
            'l-zit': 'cal_lsit',
            'l zit': 'cal_lsit',
            'lsit': 'cal_lsit',
            'max-uitdaging': 'cal_max_challenge',
            'max uitdaging': 'cal_max_challenge',
            'planche': 'cal_planche',
            'planche-houding': 'cal_planche',
            'pull-up': 'cal_pullup',
            'pull up': 'cal_pullup',
            'pullup': 'cal_pullup',
            'push-up': 'cal_pushup',
            'push up': 'cal_pushup',
            'pushup': 'cal_pushup',
            'sit-up': 'cal_situp',
            'sit up': 'cal_situp',
            'situp': 'cal_situp',
            'warm-up': 'cal_warmup',
            'warm up': 'cal_warmup',
            'warmup': 'cal_warmup',
        },
        'kickboxing': {
            'benen': 'kb_legs_kicks',
            'trappen': 'kb_legs_kicks',
            'legs': 'kb_legs_kicks',
            'kicks': 'kb_legs_kicks',
            'buikspier': 'kb_abs',
            'abs': 'kb_abs',
            'combinatie': 'kb_combinations',
            'combinations': 'kb_combinations',
            'reaction': 'kb_reaction_time',
            'rek': 'kb_stretch_relax',
            'ontspan': 'kb_stretch_relax',
            'stretch': 'kb_stretch_relax',
            'verrassingsronde': 'kb_surprise',
            'verrassing': 'kb_surprise',
            'surprise': 'kb_surprise',
            'warm-up': 'kb_warmup',
            'warm up': 'kb_warmup',
            'warmup': 'kb_warmup',
        },
        'power_yoga': {
            'blije baby': 'py_lying',
            'baby houding': 'py_lying',
            'brughouding': 'py_lying',
            'brug': 'py_lying',
            'duif': 'py_seated',
            'duif-houding': 'py_seated',
            'gebroken-kaars': 'py_lying',
            'gebroken kaars': 'py_lying',
            'gedraaide-buik': 'py_lying',
            'gedraaide buik': 'py_lying',
            'krijger': 'py_standing',
            'warrior': 'py_standing',
            'savasana': 'py_savasana',
            'spreidstand': 'py_standing',
            'verbindingsfase': 'py_connecting',
            'connecting': 'py_connecting',
            'vinyasa-staan-tot-staan': 'py_vinyasa_s2s',
            'vinyasa staan tot staan': 'py_vinyasa_s2s',
            'vinyasa-staan-tot-zit': 'py_vinyasa_s2sit',
            'vinyasa staan tot zit': 'py_vinyasa_s2sit',
            'yoga-flow': 'py_yoga_flow',
            'yoga flow': 'py_yoga_flow',
            'zonnegroet-a': 'py_sun_greeting',
            'zonnegroet-b': 'py_sun_greeting',
            'zonnegroet a': 'py_sun_greeting',
            'zonnegroet b': 'py_sun_greeting',
            'sun greeting': 'py_sun_greeting',
        }
    }
    
    def __init__(self):
        super().__init__()
        self.validator = AudioValidator()
        self.stats = {
            'total_files': 0,
            'imported': 0,
            'skipped': 0,
            'errors': 0,
            'by_sport': {},
        }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Analyze files without importing (dry run)',
        )
        parser.add_argument(
            '--import',
            action='store_true',
            dest='do_import',
            help='Actually import the audio files',
        )
        parser.add_argument(
            '--mp3-folder',
            type=str,
            default='mp3 scripts',
            help='Path to mp3 scripts folder (default: "mp3 scripts")',
        )
        parser.add_argument(
            '--goal',
            type=str,
            default='allround',
            choices=['allround', 'strength', 'flexibility'],
            help='Default goal for imported scripts (default: allround)',
        )
    
    def handle(self, *args, **options):
        analyze_only = options['analyze']
        do_import = options['do_import']
        mp3_folder = options['mp3_folder']
        default_goal = options['goal']
        
        if not analyze_only and not do_import:
            self.stdout.write(self.style.ERROR(
                'Please specify either --analyze or --import'
            ))
            return
        
        # Check if mp3 folder exists
        mp3_path = Path(mp3_folder)
        if not mp3_path.exists():
            self.stdout.write(self.style.ERROR(
                f'MP3 folder not found: {mp3_folder}'
            ))
            return
        
        mode = "ANALYSIS MODE (dry run)" if analyze_only else "IMPORT MODE"
        self.stdout.write(self.style.SUCCESS(f'\n=== {mode} ===\n'))
        
        # Process each sport folder
        for folder_name, training_type in self.FOLDER_TO_TRAINING_TYPE.items():
            sport_folder = mp3_path / folder_name
            
            if not sport_folder.exists():
                self.stdout.write(self.style.WARNING(
                    f'Sport folder not found: {sport_folder}'
                ))
                continue
            
            self.stdout.write(self.style.SUCCESS(
                f'\n--- Processing {folder_name} ({training_type}) ---'
            ))
            
            # Find all MP3 files
            mp3_files = list(sport_folder.glob('*.mp3'))
            self.stats['total_files'] += len(mp3_files)
            
            if training_type not in self.stats['by_sport']:
                self.stats['by_sport'][training_type] = {
                    'total': 0,
                    'imported': 0,
                    'skipped': 0,
                    'errors': 0,
                }
            
            self.stats['by_sport'][training_type]['total'] = len(mp3_files)
            
            for mp3_file in mp3_files:
                try:
                    result = self.process_audio_file(
                        mp3_file, 
                        training_type, 
                        default_goal,
                        analyze_only
                    )
                    
                    if result == 'imported':
                        self.stats['imported'] += 1
                        self.stats['by_sport'][training_type]['imported'] += 1
                    elif result == 'skipped':
                        self.stats['skipped'] += 1
                        self.stats['by_sport'][training_type]['skipped'] += 1
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    self.stats['by_sport'][training_type]['errors'] += 1
                    self.stdout.write(self.style.ERROR(
                        f'  ✗ Error processing {mp3_file.name}: {str(e)}'
                    ))
        
        # Print summary
        self.print_summary(analyze_only)
    
    def process_audio_file(self, mp3_file, training_type, default_goal, analyze_only):
        """Process a single audio file"""
        filename = mp3_file.name
        
        # Extract duration
        duration, error = self.validator.extract_duration(mp3_file)
        if error:
            self.stdout.write(self.style.WARNING(
                f'  ⚠ Could not extract duration from {filename}: {error}'
            ))
            return 'skipped'
        
        # Map to category
        category_name = self.map_filename_to_category(filename, training_type)
        if not category_name:
            self.stdout.write(self.style.WARNING(
                f'  ⚠ Could not map {filename} to a category'
            ))
            return 'skipped'
        
        # Get category object
        try:
            category = ScriptCategory.objects.get(
                name=category_name,
                training_type=training_type
            )
        except ScriptCategory.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                f'  ⚠ Category {category_name} not found for {filename}'
            ))
            return 'skipped'
        
        # Generate title from filename
        title = self.generate_title_from_filename(filename, training_type)
        
        # Check if script already exists with this audio
        existing = WorkoutScript.objects.filter(
            type=training_type,
            script_category=category,
            audio_nl__isnull=False
        ).first()
        
        if existing:
            self.stdout.write(self.style.WARNING(
                f'  ⊙ Skipping {filename} - category already has audio'
            ))
            return 'skipped'
        
        # Display what would be imported
        self.stdout.write(
            f'  → {filename}\n'
            f'    Title: {title}\n'
            f'    Category: {category.display_name} ({category_name})\n'
            f'    Duration: {duration:.1f} min\n'
            f'    Goal: {default_goal}'
        )
        
        if not analyze_only:
            # Actually import
            with transaction.atomic():
                script = WorkoutScript.objects.create(
                    title=title,
                    type=training_type,
                    script_category=category,
                    goal=default_goal,
                    content=f'[Audio script imported from {filename}]',
                    duration_minutes=duration,
                    language='nl',
                    is_active=True,
                )
                
                # Attach audio file
                with open(mp3_file, 'rb') as f:
                    script.audio_nl.save(mp3_file.name, File(f), save=True)
                
                script.audio_duration_nl = duration
                script.save()
                
                self.stdout.write(self.style.SUCCESS(
                    f'    ✓ Imported as script ID {script.id}'
                ))
        
        return 'imported'
    
    def map_filename_to_category(self, filename, training_type):
        """Map filename to category name using pattern matching"""
        filename_lower = filename.lower()
        
        # Remove common suffixes
        filename_lower = re.sub(r'-test.*\.mp3$', '', filename_lower)
        filename_lower = re.sub(r'test.*\.mp3$', '', filename_lower)
        filename_lower = re.sub(r'\.mp3$', '', filename_lower)
        
        # Remove sport prefix
        for sport_prefix in ['calisthenics-', 'kickboksen-', 'power-yoga-', 'power yoga-']:
            if filename_lower.startswith(sport_prefix):
                filename_lower = filename_lower[len(sport_prefix):]
                break
        
        # Try to match patterns
        patterns = self.CATEGORY_PATTERNS.get(training_type, {})
        
        for pattern, category_name in patterns.items():
            if pattern in filename_lower:
                return category_name
        
        return None
    
    def generate_title_from_filename(self, filename, training_type):
        """Generate a clean title from filename"""
        # Remove extension and test suffixes
        title = filename.replace('.mp3', '')
        title = re.sub(r'-test.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'test.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\(\d+\)$', '', title)  # Remove (1), (2) etc
        
        # Remove sport prefix
        sport_prefixes = {
            'calisthenics': 'Calisthenics-',
            'kickboxing': 'kickboksen-',
            'power_yoga': 'power-yoga-',
        }
        
        prefix = sport_prefixes.get(training_type, '')
        if prefix and title.startswith(prefix):
            title = title[len(prefix):]
        
        # Clean up
        title = title.replace('-', ' ').replace('_', ' ')
        title = ' '.join(title.split())  # Normalize whitespace
        title = title.strip()
        
        # Capitalize properly
        title = title.title()
        
        return title
    
    def print_summary(self, analyze_only):
        """Print import summary"""
        self.stdout.write(self.style.SUCCESS('\n=== SUMMARY ==='))
        self.stdout.write(f'Total files found: {self.stats["total_files"]}')
        self.stdout.write(f'Would be imported: {self.stats["imported"]}' if analyze_only else f'Imported: {self.stats["imported"]}')
        self.stdout.write(f'Skipped: {self.stats["skipped"]}')
        self.stdout.write(f'Errors: {self.stats["errors"]}')
        
        self.stdout.write('\nBy Sport:')
        for sport, stats in self.stats['by_sport'].items():
            self.stdout.write(
                f'  {sport}: {stats["imported"]}/{stats["total"]} '
                f'(skipped: {stats["skipped"]}, errors: {stats["errors"]})'
            )
        
        if analyze_only:
            self.stdout.write(self.style.WARNING(
                '\nThis was a dry run. Use --import to actually import the files.'
            ))

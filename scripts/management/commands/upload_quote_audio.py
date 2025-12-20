"""
Management command to upload quote audio files from a directory

Usage:
    python manage.py upload_quote_audio --path "C:\path\to\audio\files"
    python manage.py upload_quote_audio --path "C:\path\to\audio\files" --dry-run
"""

import os
import re
from django.core.management.base import BaseCommand
from django.core.files import File
from scripts.models import MotivationalQuote
from generator.audio_validator import AudioValidator


class Command(BaseCommand):
    help = 'Upload quote audio files and auto-extract durations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            required=True,
            help='Path to directory containing quote audio files'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be uploaded without actually uploading'
        )
        parser.add_argument(
            '--language',
            type=str,
            default='nl',
            choices=['nl', 'en'],
            help='Language of the audio files (default: nl)'
        )

    def handle(self, *args, **options):
        audio_path = options['path']
        dry_run = options['dry_run']
        language = options['language']

        if not os.path.exists(audio_path):
            self.stdout.write(self.style.ERROR(f'Path does not exist: {audio_path}'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n🎵 Quote Audio Upload Tool'))
        self.stdout.write(f'Path: {audio_path}')
        self.stdout.write(f'Language: {language}')
        self.stdout.write(f'Mode: {"DRY RUN" if dry_run else "UPLOAD"}\n')

        # Get all audio files
        audio_files = self._get_audio_files(audio_path)
        
        if not audio_files:
            self.stdout.write(self.style.WARNING('No audio files found!'))
            return

        self.stdout.write(f'Found {len(audio_files)} audio files\n')

        # Process each file
        validator = AudioValidator()
        uploaded_count = 0
        skipped_count = 0
        error_count = 0

        for file_path in audio_files:
            filename = os.path.basename(file_path)
            
            # Extract sport from filename
            sport = self._extract_sport_from_filename(filename)
            
            if not sport:
                self.stdout.write(self.style.WARNING(f'⚠️  Skipped (no sport): {filename}'))
                skipped_count += 1
                continue

            self.stdout.write(f'\n📁 Processing: {filename}')
            self.stdout.write(f'   Sport: {sport}')

            # Validate audio file
            is_valid, format_type, error = validator.validate_file_format(file_path)
            if not is_valid:
                self.stdout.write(self.style.ERROR(f'   ❌ Invalid format: {error}'))
                error_count += 1
                continue

            # Extract duration
            duration, error = validator.extract_duration(file_path)
            if error:
                self.stdout.write(self.style.ERROR(f'   ❌ Duration error: {error}'))
                error_count += 1
                continue

            self.stdout.write(f'   Duration: {duration:.2f} minutes ({duration*60:.1f} seconds)')

            # Find or create quote
            quote = self._find_or_create_quote(sport, filename, language, dry_run)
            
            if not quote:
                self.stdout.write(self.style.ERROR(f'   ❌ Could not find/create quote'))
                error_count += 1
                continue

            # Upload audio
            if dry_run:
                self.stdout.write(self.style.WARNING(f'   🔍 DRY RUN: Would upload to quote #{quote.id}'))
                uploaded_count += 1
            else:
                success = self._upload_audio(quote, file_path, duration, language)
                if success:
                    self.stdout.write(self.style.SUCCESS(f'   ✅ Uploaded to quote #{quote.id}'))
                    uploaded_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f'   ❌ Upload failed'))
                    error_count += 1

        # Summary
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS(f'📊 SUMMARY'))
        self.stdout.write(f'   Total files: {len(audio_files)}')
        self.stdout.write(self.style.SUCCESS(f'   ✅ Uploaded: {uploaded_count}'))
        self.stdout.write(self.style.WARNING(f'   ⚠️  Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'   ❌ Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(f'\n💡 Run without --dry-run to actually upload files')

    def _get_audio_files(self, directory):
        """Get all audio files from directory"""
        audio_extensions = ['.mp3', '.wav', '.m4a']
        audio_files = []
        
        for filename in os.listdir(directory):
            if any(filename.lower().endswith(ext) for ext in audio_extensions):
                audio_files.append(os.path.join(directory, filename))
        
        return sorted(audio_files)

    def _extract_sport_from_filename(self, filename):
        """
        Extract sport from filename
        Examples:
        - kickboxing-quote.mp3 -> kickboxing
        - power-yoga-quote (1).mp3 -> power_yoga
        - calisthenics-quote (2).mp3 -> calisthenics
        """
        filename_lower = filename.lower()
        
        # Map filename patterns to training_type values
        sport_patterns = {
            'kickboxing': 'kickboxing',
            'power-yoga': 'power_yoga',
            'power_yoga': 'power_yoga',
            'calisthenics': 'calisthenics',
        }
        
        for pattern, sport in sport_patterns.items():
            if pattern in filename_lower:
                return sport
        
        return None

    def _find_or_create_quote(self, sport, filename, language, dry_run):
        """
        Find existing quote without audio or create placeholder
        Tries to distribute files across different quotes
        """
        # Extract number from filename to help with distribution
        number_match = re.search(r'\((\d+)\)', filename)
        file_number = int(number_match.group(1)) if number_match else 0
        
        # Try to find quote without audio for this sport
        if language == 'nl':
            quotes = MotivationalQuote.objects.filter(
                training_type=sport,
                audio_nl__isnull=True,
                is_active=True
            ).order_by('id')
        else:
            quotes = MotivationalQuote.objects.filter(
                training_type=sport,
                audio_en__isnull=True,
                is_active=True
            ).order_by('id')
        
        quotes_list = list(quotes)
        
        if quotes_list:
            # Distribute files across available quotes using modulo
            quote_index = file_number % len(quotes_list) if file_number > 0 else 0
            quote = quotes_list[quote_index]
            self.stdout.write(f'   Found existing quote #{quote.id}: "{quote.quote_text[:50]}..."')
            return quote
        
        # Create placeholder quote
        if dry_run:
            self.stdout.write(f'   Would create placeholder quote')
            # Return a mock object for dry run
            class MockQuote:
                id = 999
            return MockQuote()
        
        quote_text = f"Motivational quote {file_number if file_number > 0 else 1} for {sport}"
        
        quote = MotivationalQuote.objects.create(
            training_type=sport,
            quote_text=quote_text,
            language=language,
            is_active=True,
            is_exercise_specific=False
        )
        
        self.stdout.write(f'   Created placeholder quote: "{quote_text}"')
        return quote

    def _upload_audio(self, quote, file_path, duration, language):
        """Upload audio file to quote and set duration"""
        try:
            filename = os.path.basename(file_path)
            
            with open(file_path, 'rb') as audio_file:
                django_file = File(audio_file, name=filename)
                
                if language == 'nl':
                    quote.audio_nl = django_file
                    quote.audio_duration_nl = duration
                else:
                    quote.audio_en = django_file
                    quote.audio_duration_en = duration
                
                quote.save()
            
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   Error: {str(e)}'))
            return False

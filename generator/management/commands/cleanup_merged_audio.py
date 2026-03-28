"""
Management command to clean up merged audio files.

Usage:
    python manage.py cleanup_merged_audio              # orphans + expired (default 2h TTL)
    python manage.py cleanup_merged_audio --hours 4   # custom TTL
    python manage.py cleanup_merged_audio --orphans-only
    python manage.py cleanup_merged_audio --expired-only
    python manage.py cleanup_merged_audio --dry-run
"""

import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from generator.models import AudioPlaylist


class Command(BaseCommand):
    help = 'Delete orphaned and/or expired merged audio files to free up disk space'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=float,
            default=getattr(settings, 'MERGED_AUDIO_TTL_HOURS', 2),
            help='Delete merged files older than this many hours (default: 2)',
        )
        parser.add_argument(
            '--orphans-only',
            action='store_true',
            help='Only delete orphaned files (no DB record)',
        )
        parser.add_argument(
            '--expired-only',
            action='store_true',
            help='Only delete expired merged files',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        orphans_only = options['orphans_only']
        expired_only = options['expired_only']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no files will be deleted\n'))

        total_deleted = 0
        total_bytes = 0

        if not expired_only:
            deleted, freed = self._cleanup_orphans(dry_run)
            total_deleted += deleted
            total_bytes += freed

        if not orphans_only:
            deleted, freed = self._cleanup_expired(hours, dry_run)
            total_deleted += deleted
            total_bytes += freed

        freed_mb = total_bytes / (1024 * 1024)
        action = 'Would free' if dry_run else 'Freed'
        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {total_deleted} file(s) processed. {action} ~{freed_mb:.2f} MB.'
        ))

    def _cleanup_orphans(self, dry_run):
        """Delete files in merged_audio/ that have no matching DB record."""
        self.stdout.write('--- Orphan cleanup ---')
        merged_dir = os.path.join(settings.MEDIA_ROOT, 'merged_audio')

        if not os.path.isdir(merged_dir):
            self.stdout.write('  merged_audio/ directory not found, skipping.')
            return 0, 0

        # All filenames currently referenced in DB
        referenced = set(
            AudioPlaylist.objects
            .exclude(merged_audio_file='')
            .exclude(merged_audio_file=None)
            .values_list('merged_audio_file', flat=True)
        )
        # Values are stored as 'merged_audio/filename.mp3' — extract just the basename
        referenced_names = {os.path.basename(p) for p in referenced}

        deleted = 0
        freed = 0
        for fname in os.listdir(merged_dir):
            if fname not in referenced_names:
                fpath = os.path.join(merged_dir, fname)
                if os.path.isfile(fpath):
                    size = os.path.getsize(fpath)
                    self.stdout.write(f'  Orphan: {fname} ({size / 1024:.0f} KB)')
                    if not dry_run:
                        os.remove(fpath)
                    deleted += 1
                    freed += size

        if deleted == 0:
            self.stdout.write('  No orphans found.')
        return deleted, freed

    def _cleanup_expired(self, hours, dry_run):
        """Delete merged files older than `hours` and clear the DB field."""
        self.stdout.write(f'--- Expired cleanup (TTL = {hours}h) ---')
        cutoff = timezone.now() - timedelta(hours=hours)

        expired_playlists = AudioPlaylist.objects.filter(
            merged_at__lt=cutoff,
        ).exclude(merged_audio_file='').exclude(merged_audio_file=None)

        deleted = 0
        freed = 0
        for playlist in expired_playlists:
            try:
                path = playlist.merged_audio_file.path
                size = os.path.getsize(path) if os.path.isfile(path) else 0
                self.stdout.write(
                    f'  Expired: {os.path.basename(path)} '
                    f'(merged {playlist.merged_at.strftime("%Y-%m-%d %H:%M")}, {size / 1024:.0f} KB)'
                )
                if not dry_run:
                    if os.path.isfile(path):
                        os.remove(path)
                    playlist.merged_audio_file.delete(save=False)
                    playlist.merged_at = None
                    playlist.save(update_fields=['merged_audio_file', 'merged_at'])
                deleted += 1
                freed += size
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error processing playlist {playlist.id}: {e}'))

        if deleted == 0:
            self.stdout.write(f'  No expired files found (older than {hours}h).')
        return deleted, freed

import os
import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import AudioPlaylist

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=AudioPlaylist)
def delete_merged_audio_file(sender, instance, **kwargs):
    """Delete merged audio file from disk when an AudioPlaylist is deleted."""
    if instance.merged_audio_file:
        try:
            path = instance.merged_audio_file.path
            if os.path.isfile(path):
                os.remove(path)
                logger.info(f"Deleted merged audio file: {path}")
        except Exception as e:
            logger.error(f"Error deleting merged audio for playlist {instance.id}: {e}")

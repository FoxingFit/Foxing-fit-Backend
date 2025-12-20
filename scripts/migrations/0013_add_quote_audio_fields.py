# Generated migration for adding audio support to MotivationalQuote

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scripts', '0012_add_audio_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='motivationalquote',
            name='audio_nl',
            field=models.FileField(
                blank=True,
                help_text='Dutch audio recording for this quote',
                null=True,
                upload_to='quote_audio/nl/'
            ),
        ),
        migrations.AddField(
            model_name='motivationalquote',
            name='audio_en',
            field=models.FileField(
                blank=True,
                help_text='English audio recording for this quote',
                null=True,
                upload_to='quote_audio/en/'
            ),
        ),
        migrations.AddField(
            model_name='motivationalquote',
            name='audio_duration_nl',
            field=models.FloatField(
                blank=True,
                help_text='Duration of Dutch audio in minutes',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='motivationalquote',
            name='audio_duration_en',
            field=models.FloatField(
                blank=True,
                help_text='Duration of English audio in minutes',
                null=True
            ),
        ),
    ]

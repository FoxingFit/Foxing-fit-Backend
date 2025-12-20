# Generated migration for AudioQuoteSegment model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0006_add_session_quote_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='AudioQuoteSegment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence_order', models.IntegerField(help_text='Order in the playlist (inserted between script segments)')),
                ('audio_file', models.FileField(blank=True, help_text='Reference to the quote audio file', null=True, upload_to='merged_audio/')),
                ('duration', models.FloatField(blank=True, help_text='Duration of this quote audio in minutes', null=True)),
                ('is_available', models.BooleanField(default=False, help_text='Whether audio is available for this quote')),
                ('pause_after', models.FloatField(default=2.0, help_text='Pause duration after this quote in seconds')),
                ('audio_playlist', models.ForeignKey(
                    help_text='Which audio playlist this quote segment belongs to',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='quote_segments',
                    to='generator.audioplaylist'
                )),
                ('session_quote', models.ForeignKey(
                    help_text='The session quote this audio represents',
                    on_delete=django.db.models.deletion.CASCADE,
                    to='generator.sessionquote'
                )),
            ],
            options={
                'verbose_name': 'Audio Quote Segment',
                'verbose_name_plural': 'Audio Quote Segments',
                'ordering': ['sequence_order'],
            },
        ),
    ]

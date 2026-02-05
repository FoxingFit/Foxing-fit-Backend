# Generated migration for SessionQuote model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0005_audioplaylist_merged_at_and_more'),
        ('scripts', '0013_add_quote_audio_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionQuote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence_order', models.IntegerField(help_text='Order in the workout (inserted between scripts)')),
                ('inserted_after_script', models.ForeignKey(
                    help_text='The script this quote was inserted after',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='quotes_after',
                    to='generator.sessionscript'
                )),
                ('motivational_quote', models.ForeignKey(
                    help_text='The motivational quote that was used',
                    on_delete=django.db.models.deletion.CASCADE,
                    to='scripts.motivationalquote'
                )),
                ('workout_session', models.ForeignKey(
                    help_text='Which workout session this quote belongs to',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='session_quotes',
                    to='generator.workoutsession'
                )),
            ],
            options={
                'verbose_name': 'Session Quote',
                'verbose_name_plural': 'Session Quotes',
                'ordering': ['sequence_order'],
            },
        ),
    ]

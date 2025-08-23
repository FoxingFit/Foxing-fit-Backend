# scripts/migrations/0006_create_system_categories.py

from django.db import migrations

def create_system_categories(apps, schema_editor):
    """Auto-create the 4 required system categories"""
    ScriptCategory = apps.get_model('scripts', 'ScriptCategory')
    
    system_categories = [
        {
            'name': 'kb_surprise',
            'training_type': 'kickboxing',
            'display_name': 'Surprise Rounds',
            'description': 'System category for automatic surprise round insertion',
            'is_system_category': True,
            'is_active': True,
        },
        {
            'name': 'cal_max_challenge',
            'training_type': 'calisthenics',
            'display_name': 'MAX Challenge',
            'description': 'System category for MAX challenge rounds placed at workout end',
            'is_system_category': True,
            'is_active': True,
        },
        {
            'name': 'py_vinyasa_s2s',
            'training_type': 'power_yoga',
            'display_name': 'Vinyasa Standing-to-Standing',
            'description': 'System category for standing-to-standing flow transitions',
            'is_system_category': True,
            'is_active': True,
        },
        {
            'name': 'py_vinyasa_s2sit',
            'training_type': 'power_yoga',
            'display_name': 'Vinyasa Standing-to-Sitting',
            'description': 'System category for standing-to-sitting flow transitions',
            'is_system_category': True,
            'is_active': True,
        },
    ]
    
    for category_data in system_categories:
        # Only create if doesn't exist
        if not ScriptCategory.objects.filter(
            name=category_data['name'], 
            training_type=category_data['training_type']
        ).exists():
            ScriptCategory.objects.create(**category_data)

def reverse_system_categories(apps, schema_editor):
    """Remove system categories if rolling back"""
    ScriptCategory = apps.get_model('scripts', 'ScriptCategory')
    system_names = ['kb_surprise', 'cal_max_challenge', 'py_vinyasa_s2s', 'py_vinyasa_s2sit']
    ScriptCategory.objects.filter(name__in=system_names).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('scripts', '0005_alter_scriptcategory_options_and_more'),  # Your existing migration
    ]

    operations = [
        # Auto-create system categories
        migrations.RunPython(
            create_system_categories,
            reverse_system_categories,
        ),
    ]
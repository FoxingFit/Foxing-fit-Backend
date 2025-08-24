# Create: scripts/management/commands/convert_to_utf8mb4.py
# Alternative to running SQL manually

from django.core.management.base import BaseCommand
from django.db import connection, transaction

class Command(BaseCommand):
    help = 'Convert MySQL tables to utf8mb4 charset for emoji support'
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                          help='Preview changes without executing')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be made"))
        
        # Tables that need utf8mb4 conversion
        tables_to_convert = [
            'generator_workoutsession',
            'generator_sessionscript', 
            'scripts_workoutscript',
            'scripts_motivationalquote',
            'scripts_scriptcategory',
            'scripts_workouttemplate',
        ]
        
        # Specific columns that definitely need utf8mb4
        specific_columns = [
            ('generator_workoutsession', 'compiled_script', 'LONGTEXT'),
            ('generator_workoutsession', 'title', 'VARCHAR(200)'),
            ('scripts_workoutscript', 'content', 'LONGTEXT'),
            ('scripts_workoutscript', 'title', 'VARCHAR(200)'),
            ('scripts_motivationalquote', 'quote_text', 'LONGTEXT'),
            ('scripts_scriptcategory', 'display_name', 'VARCHAR(100)'),
        ]
        
        try:
            with connection.cursor() as cursor:
                # Get current database name
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                self.stdout.write(f"📊 Working with database: {db_name}")
                
                # Check current database charset
                cursor.execute(f"SHOW CREATE DATABASE `{db_name}`")
                db_info = cursor.fetchone()[1]
                self.stdout.write(f"🔍 Current database info: {db_info}")
                
                if not dry_run:
                    # Convert database default charset
                    self.stdout.write("🔄 Converting database charset to utf8mb4...")
                    cursor.execute(f"ALTER DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    self.stdout.write("✅ Database charset converted")
                
                # Convert tables
                self.stdout.write(f"\n🔄 Converting {len(tables_to_convert)} tables...")
                for table in tables_to_convert:
                    if not dry_run:
                        cursor.execute(f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                        self.stdout.write(f"✅ Converted table: {table}")
                    else:
                        self.stdout.write(f"[DRY RUN] Would convert table: {table}")
                
                # Convert specific columns
                self.stdout.write(f"\n🎯 Converting {len(specific_columns)} specific columns...")
                for table, column, data_type in specific_columns:
                    if not dry_run:
                        cursor.execute(f"""
                            ALTER TABLE `{table}` 
                            MODIFY COLUMN `{column}` {data_type} 
                            CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                        """)
                        self.stdout.write(f"✅ Converted {table}.{column}")
                    else:
                        self.stdout.write(f"[DRY RUN] Would convert {table}.{column}")
                
                if not dry_run:
                    # Verify one important table
                    cursor.execute("SHOW CREATE TABLE generator_workoutsession")
                    table_info = cursor.fetchone()[1]
                    
                    if 'utf8mb4' in table_info:
                        self.stdout.write(self.style.SUCCESS("\n🎉 SUCCESS! Tables converted to utf8mb4"))
                        self.stdout.write("✨ Your database now supports emojis!")
                    else:
                        self.stdout.write(self.style.WARNING("\n⚠️ Conversion may not have worked correctly"))
                else:
                    self.stdout.write(self.style.SUCCESS("\n✅ Dry run completed"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {str(e)}"))
            self.stdout.write("💡 Try running the SQL commands manually in PythonAnywhere MySQL console")
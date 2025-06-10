"""
Django management command to rename existing uploaded files to match the new camelCase format
and update the database accordingly.

Usage:
    python manage.py rename_to_new_format
    python manage.py rename_to_new_format --dry-run
    python manage.py rename_to_new_format --force
"""

import os
import re
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from image_upload.models import Image


class Command(BaseCommand):
    help = 'Rename uploaded files to new camelCase format and update database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without making them',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.HTTP_INFO('STL Collection File Rename Command')
        )
        self.stdout.write('=' * 60)

        # Get all images from database
        images = Image.objects.all().order_by('upload_date')
        
        self.stdout.write(f'Found {images.count()} images in database')
        self.stdout.write('')

        # First, do a dry run to show what would be renamed
        self.stdout.write(
            self.style.WARNING('DRY RUN - Analyzing files')
        )
        self.stdout.write('-' * 30)

        files_to_rename = []
        for image in images:
            result = self.analyze_file(image)
            if result:
                files_to_rename.append(image)

        self.stdout.write('')
        self.stdout.write(f'Summary: {len(files_to_rename)} files need to be renamed')

        if not files_to_rename:
            self.stdout.write(
                self.style.SUCCESS('All files are already in the correct format!')
            )
            return

        # If this is just a dry run, stop here
        if options['dry_run']:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('Dry run completed. Remove --dry-run to perform actual renaming.')
            )
            return

        # Ask for confirmation unless force is specified
        if not options['force']:
            self.stdout.write('')
            confirm = input('Do you want to proceed with the actual renaming? (y/N): ')
            
            if confirm.lower() != 'y':
                self.stdout.write('Operation cancelled.')
                return

        # Perform actual renaming
        self.stdout.write('')
        self.stdout.write(
            self.style.HTTP_INFO('ACTUAL RENAMING - Making changes')
        )
        self.stdout.write('-' * 40)

        success_count = 0
        error_count = 0

        for image in files_to_rename:
            if self.rename_file(image):
                success_count += 1
            else:
                error_count += 1

        # Final summary
        self.stdout.write('')
        self.stdout.write(
            self.style.HTTP_INFO('FINAL SUMMARY')
        )
        self.stdout.write('=' * 20)
        
        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully renamed: {success_count} files')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'Errors encountered: {error_count} files')
            )
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('Please review the errors above and fix any issues manually.')
            )
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('All files have been successfully renamed to the new format!')
            )

    def to_camel_case(self, text):
        """Convert text to camelCase format"""
        if not text:
            return "unknown"
        # Remove special characters and split by spaces/underscores/hyphens
        words = re.split(r'[^a-zA-Z0-9]+', str(text).strip())
        # Filter out empty strings
        words = [word for word in words if word]
        if not words:
            return "unknown"
        # First word lowercase, rest title case
        camel_case = words[0].lower()
        for word in words[1:]:
            camel_case += word.capitalize()
        return camel_case

    def generate_new_filename(self, image_obj):
        """Generate new filename in the format: publisher_range_name_initial.ext"""
        # Get file extension
        if image_obj.image and image_obj.image.name:
            _, ext = os.path.splitext(image_obj.image.name)
        else:
            ext = '.jpg'  # Default extension
        
        # Create new filename using camelCase format
        publisher = self.to_camel_case(image_obj.publisher)
        range_name = self.to_camel_case(image_obj.range)
        name = self.to_camel_case(image_obj.name)
        
        # Create filename in format: publisher_range_name_initial.ext
        new_filename = f"{publisher}_{range_name}_{name}_initial{ext}"
        return new_filename

    def is_new_format(self, filename):
        """Check if filename already follows the new format"""
        # New format should end with '_initial' before the extension
        base_name = os.path.splitext(filename)[0]
        return base_name.endswith('_initial')

    def analyze_file(self, image_obj):
        """Analyze if a file needs renaming and show what would happen"""
        if not image_obj.image:
            self.stdout.write(
                self.style.WARNING(f"Skipping '{image_obj.name}' - No file associated")
            )
            return False
        
        current_name = os.path.basename(image_obj.image.name)
        
        # Skip if already in new format
        if self.is_new_format(current_name):
            self.stdout.write(f"Skipping '{current_name}' - Already in new format")
            return False
        
        # Check if file exists
        if not os.path.exists(image_obj.image.path):
            self.stdout.write(
                self.style.WARNING(f"Skipping '{current_name}' - File not found")
            )
            return False
        
        # Generate new filename
        new_filename = self.generate_new_filename(image_obj)
        
        self.stdout.write(f"Rename: {current_name} -> {new_filename}")
        return True

    def rename_file(self, image_obj):
        """Actually rename a file and update the database"""
        current_path = image_obj.image.path
        current_name = os.path.basename(current_path)
        
        # Generate new filename
        new_filename = self.generate_new_filename(image_obj)
        new_path = os.path.join(os.path.dirname(current_path), new_filename)
        
        self.stdout.write(f"Renaming: {current_name} -> {new_filename}")
        
        try:
            # Check if new filename already exists
            if os.path.exists(new_path):
                self.stdout.write(
                    self.style.ERROR(f"  ERROR: Target file already exists: {new_filename}")
                )
                return False
            
            # Rename the physical file
            os.rename(current_path, new_path)
            
            # Update the database record
            image_obj.image.name = f"uploaded_images/{new_filename}"
            image_obj.save(update_fields=['image'])
            
            self.stdout.write(
                self.style.SUCCESS(f"  SUCCESS: Renamed and updated database")
            )
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ERROR: {str(e)}")
            )
            # Try to restore original file if rename succeeded but DB update failed
            if os.path.exists(new_path) and not os.path.exists(current_path):
                try:
                    os.rename(new_path, current_path)
                    self.stdout.write(
                        self.style.WARNING(f"  Restored original file")
                    )
                except:
                    pass
            return False

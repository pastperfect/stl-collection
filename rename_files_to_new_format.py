#!/usr/bin/env python
"""
Script to rename existing uploaded files to match the new camelCase format
and update the database accordingly.

New format: {publisher}_{range}_{name}_initial.{ext}
All components are converted to camelCase.
"""

import os
import sys
import django
from pathlib import Path
import re

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stl_collection.settings')
django.setup()

from image_upload.models import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def to_camel_case(text):
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

def generate_new_filename(image_obj):
    """Generate new filename in the format: publisher_range_name_initial.ext"""
    # Get file extension
    if image_obj.image and image_obj.image.name:
        _, ext = os.path.splitext(image_obj.image.name)
    else:
        ext = '.jpg'  # Default extension
    
    # Create new filename using camelCase format
    publisher = to_camel_case(image_obj.publisher)
    range_name = to_camel_case(image_obj.range)
    name = to_camel_case(image_obj.name)
    
    # Create filename in format: publisher_range_name_initial.ext
    new_filename = f"{publisher}_{range_name}_{name}_initial{ext}"
    return new_filename

def is_new_format(filename):
    """Check if filename already follows the new format"""
    # New format should end with '_initial' before the extension
    base_name = os.path.splitext(filename)[0]
    return base_name.endswith('_initial')

def rename_file_and_update_db(image_obj, dry_run=True):
    """Rename a file and update the database record"""
    if not image_obj.image:
        print(f"Skipping {image_obj.name} - No file associated")
        return False
    
    current_path = image_obj.image.path
    current_name = os.path.basename(current_path)
    
    # Skip if already in new format
    if is_new_format(current_name):
        print(f"Skipping {current_name} - Already in new format")
        return False
    
    # Generate new filename
    new_filename = generate_new_filename(image_obj)
    new_path = os.path.join(os.path.dirname(current_path), new_filename)
    
    print(f"Rename: {current_name} -> {new_filename}")
    
    if not dry_run:
        try:
            # Check if new filename already exists
            if os.path.exists(new_path):
                print(f"  ERROR: Target file already exists: {new_filename}")
                return False
            
            # Rename the physical file
            os.rename(current_path, new_path)
            
            # Update the database record
            image_obj.image.name = f"uploaded_images/{new_filename}"
            image_obj.save(update_fields=['image'])
            
            print(f"  SUCCESS: Renamed and updated database")
            return True
            
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            # Try to restore original file if rename succeeded but DB update failed
            if os.path.exists(new_path) and not os.path.exists(current_path):
                try:
                    os.rename(new_path, current_path)
                    print(f"  Restored original file")
                except:
                    pass
            return False
    
    return True  # Dry run success

def main():
    """Main function to process all images"""
    print("STL Collection File Rename Script")
    print("=" * 50)
    
    # Get all images from database
    images = Image.objects.all().order_by('upload_date')
    
    print(f"Found {images.count()} images in database")
    print()
    
    # First, do a dry run
    print("DRY RUN - No changes will be made")
    print("-" * 30)
    
    files_to_rename = []
    for image in images:
        if rename_file_and_update_db(image, dry_run=True):
            if image.image and not is_new_format(os.path.basename(image.image.name)):
                files_to_rename.append(image)
    
    print()
    print(f"Summary: {len(files_to_rename)} files need to be renamed")
    
    if not files_to_rename:
        print("All files are already in the correct format!")
        return
    
    # Ask for confirmation
    print()
    response = input("Do you want to proceed with the actual renaming? (y/N): ")
    
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Perform actual renaming
    print()
    print("ACTUAL RENAMING - Making changes")
    print("-" * 30)
    
    success_count = 0
    error_count = 0
    
    for image in files_to_rename:
        if rename_file_and_update_db(image, dry_run=False):
            success_count += 1
        else:
            error_count += 1
    
    print()
    print("FINAL SUMMARY")
    print("=" * 20)
    print(f"Successfully renamed: {success_count} files")
    print(f"Errors encountered: {error_count} files")
    
    if error_count > 0:
        print("\nPlease review the errors above and fix any issues manually.")
    else:
        print("\nAll files have been successfully renamed to the new format!")

if __name__ == "__main__":
    main()

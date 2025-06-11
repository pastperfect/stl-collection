#!/usr/bin/env python
"""
Script to create sample data for the STL Collection Manager
Run this with: python manage.py shell < create_sample_data.py
"""

from tags.models import Tag
from image_upload.models import Image
from django.contrib.auth.models import User

# Create sample tags
sample_tags = [
    'Fantasy', 'Sci-Fi', 'Medieval', 'Modern', 'Vehicles', 'Characters', 
    'Buildings', 'Terrain', 'Weapons', 'Miniatures', 'Tabletop', 'D&D'
]

print("Creating sample tags...")
for tag_name in sample_tags:
    tag, created = Tag.objects.get_or_create(name=tag_name)
    if created:
        print(f"Created tag: {tag_name}")
    else:
        print(f"Tag already exists: {tag_name}")

print(f"\nTotal tags in database: {Tag.objects.count()}")

# Create a test superuser if it doesn't exist
if not User.objects.filter(username='admin').exists():
    print("\nCreating admin user...")
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Admin user created (username: admin, password: admin123)")
else:
    print("\nAdmin user already exists")

print("\nSample data creation completed!")
print("You can now:")
print("1. Visit the admin interface at /admin/ (username: admin, password: admin123)")
print("2. Upload some STL files through the upload interface")
print("3. Assign tags to your uploads")
print("4. Browse the collection gallery")

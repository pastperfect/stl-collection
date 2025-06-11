#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stl_collection.settings')
django.setup()

from tags.models import TagType, Tag

print("TagTypes in database:")
tag_types = TagType.objects.all()
if tag_types:
    for tt in tag_types:
        print(f"- {tt.name} (active: {tt.is_active}, color: {tt.color})")
else:
    print("No TagTypes found!")

print(f"\nTotal TagTypes: {tag_types.count()}")
print(f"Active TagTypes: {TagType.objects.filter(is_active=True).count()}")

print("\nTags and their types:")
tags = Tag.objects.all()
for tag in tags:
    print(f"- {tag.name}: {tag.tag_type.name if tag.tag_type else 'No Type'}")

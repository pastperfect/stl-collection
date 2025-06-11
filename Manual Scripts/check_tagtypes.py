#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stl_collection.settings')
django.setup()

from tags.models import TagType, Tag

print("TagTypes created:")
for tt in TagType.objects.all():
    print(f"  {tt.name} (ID: {tt.id}, Color: {tt.color}, Sort: {tt.sort_order})")

print(f"\nTotal tags: {Tag.objects.count()}")
print("Sample tags with their types:")
for t in Tag.objects.all()[:10]:
    tag_type_name = t.tag_type.name if t.tag_type else "No TagType"
    print(f"  {t.name} -> {tag_type_name}")

print("\nTags without TagType:")
no_type_count = Tag.objects.filter(tag_type__isnull=True).count()
print(f"  {no_type_count} tags without TagType")

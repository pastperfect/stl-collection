#!/usr/bin/env python
"""
Quick test to check ranges data
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stl_collection.settings')
django.setup()

from django.db.models import Count, Q
from image_upload.models import Image

# Test basic query
images_with_ranges = Image.objects.exclude(range__isnull=True).exclude(range__exact='')
print(f"Total images with ranges: {images_with_ranges.count()}")

# Test range aggregation
ranges_data = (
    Image.objects
    .exclude(range__isnull=True)
    .exclude(range__exact='')
    .values('range')
    .annotate(image_count=Count('id'))
    .order_by('-image_count')
)

print(f"Total unique ranges: {ranges_data.count()}")
print("\nTop 10 ranges:")
for item in ranges_data[:10]:
    print(f"  {item['range']}: {item['image_count']} images")

# Test publishers
publishers = (
    Image.objects
    .exclude(publisher__isnull=True)
    .exclude(publisher__exact='')
    .exclude(range__isnull=True)
    .exclude(range__exact='')
    .values_list('publisher', flat=True)
    .distinct()
    .order_by('publisher')
)

print(f"\nPublishers with ranges: {publishers.count()}")
for pub in publishers[:5]:
    print(f"  {pub}")

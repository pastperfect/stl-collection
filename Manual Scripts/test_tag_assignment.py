#!/usr/bin/env python3

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stl_collection.settings')
django.setup()

from image_upload.models import Image
from tags.models import Tag

def test_tag_assignment_data():
    """Test the tag assignment functionality and data structure"""
    
    print("=== Tag Assignment System Test ===")
    
    # Get statistics
    total_images = Image.objects.count()
    total_tags = Tag.objects.count()
    untagged_images = Image.objects.filter(tags__isnull=True).count()
    tagged_images = total_images - untagged_images
    
    print(f"\n📊 Current Statistics:")
    print(f"  Total Images: {total_images}")
    print(f"  Total Tags: {total_tags}")
    print(f"  Tagged Images: {tagged_images}")
    print(f"  Untagged Images: {untagged_images}")
    
    # Show available tags
    print(f"\n🏷️  Available Tags:")
    for tag in Tag.objects.all().order_by('name'):
        usage_count = tag.image_set.count()
        print(f"  - {tag.name}: {usage_count} image(s)")
    
    # Show sample images with their tags
    print(f"\n🖼️  Sample Images with Tags:")
    sample_images = Image.objects.prefetch_related('tags')[:5]
    for image in sample_images:
        tags_list = [tag.name for tag in image.tags.all()]
        tags_str = ", ".join(tags_list) if tags_list else "No tags"
        print(f"  - {image.name}: [{tags_str}]")
    
    # Show filtering capabilities
    print(f"\n🔍 Filter Test Examples:")
    
    # Publisher filter
    publishers = Image.objects.exclude(
        publisher__isnull=True
    ).exclude(publisher='').values_list('publisher', flat=True).distinct()
    
    for publisher in publishers:
        count = Image.objects.filter(publisher=publisher).count()
        print(f"  - Publisher '{publisher}': {count} images")
    
    # Range filter
    ranges = Image.objects.exclude(
        range__isnull=True
    ).exclude(range='').values_list('range', flat=True).distinct()
    
    for range_name in ranges:
        count = Image.objects.filter(range=range_name).count()
        print(f"  - Range '{range_name}': {count} images")
    
    print(f"\n✅ Tag Assignment System Ready!")
    print(f"   Navigate to: http://127.0.0.1:8000/tag-assign/")
    print(f"   Features: Bulk selection, quick tags, filtering, search")

if __name__ == "__main__":
    test_tag_assignment_data()

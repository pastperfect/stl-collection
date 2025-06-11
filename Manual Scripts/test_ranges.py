#!/usr/bin/env python
"""
Test script for ranges functionality
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stl_collection.settings')
django.setup()

from django.db.models import Count, Q
from image_upload.models import Image

def test_ranges_functionality():
    """Test the ranges functionality"""
    print("=== Testing Ranges Functionality ===\n")
    
    # Test 1: Get all ranges with counts
    print("1. Testing range aggregation...")
    ranges_data = (
        Image.objects
        .exclude(range__isnull=True)
        .exclude(range__exact='')
        .values('range', 'publisher')
        .annotate(image_count=Count('id'))
        .order_by('range', 'publisher')
    )
    
    print(f"   Found {ranges_data.count()} range-publisher combinations")
    
    # Group by range
    ranges_grouped = {}
    total_ranges = 0
    total_images = 0
    
    for item in ranges_data:
        range_name = item['range']
        publisher = item['publisher'] or 'Unknown Publisher'
        count = item['image_count']
        
        if range_name not in ranges_grouped:
            ranges_grouped[range_name] = {
                'name': range_name,
                'publishers': {},
                'total_count': 0
            }
            total_ranges += 1
        
        ranges_grouped[range_name]['publishers'][publisher] = count
        ranges_grouped[range_name]['total_count'] += count
        total_images += count
    
    print(f"   Total unique ranges: {total_ranges}")
    print(f"   Total images with ranges: {total_images}")
    
    # Test 2: Show top 5 ranges by image count
    print("\n2. Top 5 ranges by image count:")
    top_ranges = sorted(ranges_grouped.values(), key=lambda x: x['total_count'], reverse=True)[:5]
    
    for i, range_data in enumerate(top_ranges, 1):
        print(f"   {i}. {range_data['name']}: {range_data['total_count']} images")
        for publisher, count in range_data['publishers'].items():
            print(f"      - {publisher}: {count}")
    
    # Test 3: Test search functionality
    print("\n3. Testing search functionality...")
    search_query = "astro"  # Example search
    filtered_ranges = ranges_data.filter(
        Q(range__icontains=search_query) |
        Q(publisher__icontains=search_query)
    )
    print(f"   Search for '{search_query}': {filtered_ranges.count()} results")
    
    # Test 4: Test publisher filtering
    print("\n4. Testing publisher filtering...")
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
    
    print(f"   Total publishers with ranges: {publishers.count()}")
    if publishers:
        test_publisher = publishers[0]
        publisher_ranges = ranges_data.filter(publisher__icontains=test_publisher)
        print(f"   Publisher '{test_publisher}': {publisher_ranges.count()} range entries")
    
    # Test 5: Test individual range detail
    print("\n5. Testing range detail functionality...")
    if ranges_grouped:
        test_range = list(ranges_grouped.keys())[0]
        range_images = Image.objects.filter(range__iexact=test_range)
        print(f"   Range '{test_range}': {range_images.count()} images")
        
        # Test search within range
        range_search = range_images.filter(
            Q(name__icontains="test") |
            Q(publisher__icontains="test") |
            Q(tags__name__icontains="test")
        ).distinct()
        print(f"   Search within range: {range_search.count()} results")
    
    print("\n=== All tests completed successfully! ===")

if __name__ == "__main__":
    test_ranges_functionality()

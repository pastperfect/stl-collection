from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from image_upload.models import Image

@login_required
def range_list(request):
    """List all ranges with counts, search and filtering"""
    # Get all ranges with image counts
    ranges_data = (
        Image.objects
        .exclude(range__isnull=True)
        .exclude(range__exact='')
        .values('range', 'publisher')
        .annotate(image_count=Count('id'))
        .order_by('range', 'publisher')
    )
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        ranges_data = ranges_data.filter(
            Q(range__icontains=search_query) |
            Q(publisher__icontains=search_query)
        )
    
    # Filter by publisher
    publisher_filter = request.GET.get('publisher', '')
    if publisher_filter:
        ranges_data = ranges_data.filter(publisher__icontains=publisher_filter)
    
    # Get unique publishers for filter dropdown
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
    
    # Group ranges data by range name for better display
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
    
    # Convert to list and sort by range name
    ranges_list = sorted(ranges_grouped.values(), key=lambda x: x['name'].lower())
    
    # Pagination
    paginator = Paginator(ranges_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'ranges/list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'publisher_filter': publisher_filter,
        'publishers': publishers,
        'total_ranges': total_ranges,
        'total_images': total_images,
    })

@login_required
def range_detail(request, range_name):
    """Show detailed view of a specific range"""
    # Get all images in this range
    images = Image.objects.filter(range__iexact=range_name)
    
    if not images.exists():
        # Handle case where range doesn't exist
        return render(request, 'ranges/detail.html', {
            'range_name': range_name,
            'error': 'Range not found'
        })
    
    # Filter by publisher if specified
    publisher_filter = request.GET.get('publisher', '')
    if publisher_filter:
        images = images.filter(publisher__icontains=publisher_filter)
    
    # Search within the range
    search_query = request.GET.get('search', '')
    if search_query:
        images = images.filter(
            Q(name__icontains=search_query) |
            Q(publisher__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    # Get publishers for this range
    publishers = (
        Image.objects
        .filter(range__iexact=range_name)
        .exclude(publisher__isnull=True)
        .exclude(publisher__exact='')
        .values_list('publisher', flat=True)
        .distinct()
        .order_by('publisher')
    )
    
    # Get range statistics
    range_stats = (
        Image.objects
        .filter(range__iexact=range_name)
        .values('publisher')
        .annotate(count=Count('id'))
        .order_by('publisher')
    )
    
    # Pagination
    paginator = Paginator(images, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'ranges/detail.html', {
        'range_name': range_name,
        'page_obj': page_obj,
        'search_query': search_query,
        'publisher_filter': publisher_filter,
        'publishers': publishers,
        'range_stats': range_stats,
        'total_images': images.count(),
    })

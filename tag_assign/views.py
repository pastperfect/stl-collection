from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib import messages
import json

from image_upload.models import Entry, Image
from tags.models import Tag, TagType

@staff_member_required
def assign_tags(request):
    """Bulk tag assignment interface - staff only"""
      # Get filter parameters
    search_query = request.GET.get('search', '')
    publisher_filter = request.GET.get('publisher', '')
    range_filter = request.GET.get('range', '')
    tag_filter = request.GET.get('tag_filter', '')
    tag_type_filter = request.GET.get('tag_type', '')
    missing_tag_type_filter = request.GET.get('missing_tag_type', '')
    untagged_only = request.GET.get('untagged_only') == 'on'
    
    # Start with all entries
    entries = Entry.objects.all().prefetch_related('tags', 'images')
      # Apply filters
    if search_query:
        entries = entries.filter(
            Q(name__icontains=search_query) |
            Q(publisher__icontains=search_query) |
            Q(range__icontains=search_query)
        )
    
    if publisher_filter:
        entries = entries.filter(publisher=publisher_filter)
    
    if range_filter:
        entries = entries.filter(range=range_filter)
    
    if tag_filter:
        entries = entries.filter(tags__name=tag_filter)
    
    if untagged_only:
        entries = entries.filter(tags__isnull=True)
    
    # Filter for entries missing any tags of a specific tag type
    if missing_tag_type_filter:
        try:
            tag_type_id = int(missing_tag_type_filter)
            # Get all entries that have at least one tag of this type
            entries_with_tag_type = Entry.objects.filter(
                tags__tag_type_id=tag_type_id
            ).values_list('id', flat=True)
            # Exclude those entries to get entries without any tags of this type
            entries = entries.exclude(id__in=entries_with_tag_type)
        except (ValueError, TypeError):
            # If conversion fails, ignore the filter
            pass
    
    # Order by upload date (newest first)
    entries = entries.order_by('-upload_date')
      # Pagination
    paginator = Paginator(entries, 24)  # Show 24 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all available options for filters
    all_publishers = Entry.objects.exclude(
        Q(publisher__isnull=True) | Q(publisher='')
    ).values_list('publisher', flat=True).distinct().order_by('publisher')
    
    all_ranges = Entry.objects.exclude(
        Q(range__isnull=True) | Q(range='')
    ).values_list('range', flat=True).distinct().order_by('range')
    
    all_tags = Tag.objects.all().order_by('tag_type__sort_order', 'tag_type__name', 'name')
    
    # Variables for reference tag filter
    selected_tag_type_obj = None
    reference_tags = []
    reference_tag_filter = request.GET.get('reference_tag', '')
    
    # Filter quick tags by type if specified
    quick_tags = all_tags
    if tag_type_filter:
        try:
            tag_type_id = int(tag_type_filter)
            quick_tags = quick_tags.filter(tag_type_id=tag_type_id)
            
            # Get the selected tag type object to check for reference_tagtypes
            selected_tag_type_obj = TagType.objects.filter(id=tag_type_id).first()
            
            # If this tag type has reference_tagtypes, get those tags for the filter
            if selected_tag_type_obj and selected_tag_type_obj.reference_tagtypes.exists():
                reference_tags = Tag.objects.filter(
                    tag_type__in=selected_tag_type_obj.reference_tagtypes.all()
                ).order_by('name')
        except (ValueError, TypeError):
            # If conversion fails, show all tags
            pass
    
    # Apply reference tag filter if provided
    if reference_tag_filter and tag_type_filter:
        if reference_tag_filter == 'none':
            quick_tags = quick_tags.filter(reference_tags__isnull=True)
        else:
            try:
                reference_tag_id = int(reference_tag_filter)
                quick_tags = quick_tags.filter(reference_tags__id=reference_tag_id)
            except (ValueError, TypeError):
                pass
    
    # Get all tag types for the filter dropdown
    tag_types = TagType.objects.filter(is_active=True).order_by('sort_order', 'name')
      # Statistics
    total_entries = Entry.objects.count()
    untagged_count = Entry.objects.filter(tags__isnull=True).count()
    tagged_count = total_entries - untagged_count
    
    context = {
        'page_obj': page_obj,
        'all_publishers': all_publishers,
        'all_ranges': all_ranges,
        'all_tags': all_tags,
        'quick_tags': quick_tags,
        'tag_types': tag_types,
        'search_query': search_query,
        'publisher_filter': publisher_filter,
        'range_filter': range_filter,
        'tag_filter': tag_filter,
        'tag_type_filter': tag_type_filter,
        'missing_tag_type_filter': missing_tag_type_filter,
        'untagged_only': untagged_only,
        'total_entries': total_entries,
        'untagged_count': untagged_count,
        'tagged_count': tagged_count,
        'filtered_count': page_obj.paginator.count,
        'selected_tag_type_obj': selected_tag_type_obj,
        'reference_tags': reference_tags,
        'reference_tag_filter': reference_tag_filter,
    }
    
    return render(request, 'tag_assign/assign.html', context)

@staff_member_required
@require_POST
def bulk_assign_tags(request):
    """Handle bulk tag assignment via AJAX"""
    try:
        data = json.loads(request.body)
        entry_ids = data.get('entry_ids', [])
        tag_ids = data.get('tag_ids', [])
        action = data.get('action', 'add')  # 'add' or 'remove'
        
        if not entry_ids or not tag_ids:
            return JsonResponse({'success': False, 'error': 'Missing entry IDs or tag IDs'})
        
        entries = Entry.objects.filter(id__in=entry_ids)
        tags = Tag.objects.filter(id__in=tag_ids).select_related('tag_type').prefetch_related('reference_tags')
        
        affected_count = 0
        auto_assigned_count = 0
        
        for entry in entries:
            if action == 'add':
                for tag in tags:
                    entry.tags.add(tag)
                    affected_count += 1
                    
                    # Auto-assign reference tags if configured
                    for ref_tag in tag.reference_tags.all():
                        entry.tags.add(ref_tag)
                        auto_assigned_count += 1
            elif action == 'remove':
                for tag in tags:
                    entry.tags.remove(tag)
                    affected_count += 1
        
        message = f'Successfully {"added" if action == "add" else "removed"} tags for {len(entries)} entr{"y" if len(entries) == 1 else "ies"}'
        if auto_assigned_count > 0:
            message += f' (also auto-assigned {auto_assigned_count} reference tag{"s" if auto_assigned_count != 1 else ""})'
        
        return JsonResponse({
            'success': True,
            'affected_count': affected_count,
            'auto_assigned_count': auto_assigned_count,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_POST  
def quick_tag_assign(request):
    """Quick single tag assignment via AJAX"""
    try:
        data = json.loads(request.body)
        entry_id = data.get('entry_id')
        tag_id = data.get('tag_id')
        action = data.get('action', 'toggle')  # 'toggle', 'add', or 'remove'
        
        if not entry_id or not tag_id:
            return JsonResponse({'success': False, 'error': 'Missing entry ID or tag ID'})
        
        entry = get_object_or_404(Entry, id=entry_id)
        tag = get_object_or_404(Tag, id=tag_id)
        
        auto_assigned = False
        
        if action == 'toggle':
            if tag in entry.tags.all():
                entry.tags.remove(tag)
                assigned = False
            else:
                entry.tags.add(tag)
                assigned = True
                # Auto-assign reference tags if configured
                if tag.reference_tags.exists():
                    entry.tags.add(*tag.reference_tags.all())
                    auto_assigned = True
        elif action == 'add':
            entry.tags.add(tag)
            assigned = True
            # Auto-assign reference tags if configured
            if tag.reference_tags.exists():
                entry.tags.add(*tag.reference_tags.all())
                auto_assigned = True
        elif action == 'remove':
            entry.tags.remove(tag)
            assigned = False
        
        return JsonResponse({
            'success': True,
            'assigned': assigned,
            'auto_assigned': auto_assigned,
            'tag_count': entry.tags.count()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

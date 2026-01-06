from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.core.files.base import ContentFile
from image_upload.models import Entry, Image
from image_upload.forms import EntryEditForm
from tags.models import Tag, TagType
import os
import re
import uuid

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

@login_required
def gallery(request):
    """Gallery view with search and filtering"""
    entries = Entry.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        entries = entries.filter(
            Q(name__icontains=search_query) |
            Q(publisher__icontains=search_query) |
            Q(range__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    # Filter by publisher
    publisher_filter = request.GET.get('publisher', '')
    if publisher_filter:
        entries = entries.filter(publisher__icontains=publisher_filter)
    
    # Filter by range
    range_filter = request.GET.get('range', '')
    if range_filter:
        entries = entries.filter(range__icontains=range_filter)
    
    # Get tag types for filters
    tag_types = TagType.objects.filter(is_active=True, show_in_gallery=True).order_by('sort_order', 'name')
    
    # Filter by individual tag type selections (AND logic - entry must have ALL selected tags)
    tag_filter = []
    selected_tags = {}  # Track which tag is selected for each tag type
    
    for tag_type in tag_types:
        tag_param = request.GET.get(f'tag_type_{tag_type.id}', '')
        if tag_param:
            try:
                tag_id = int(tag_param)
                # Add to filter list for display purposes
                tag_filter.append(str(tag_id))
                # Track the selection
                selected_tags[tag_type.id] = tag_id
                # Filter entries that have this specific tag
                entries = entries.filter(tags__id=tag_id)
            except (ValueError, TypeError):
                pass
    
    if tag_filter:
        entries = entries.distinct()
    
    # Get filter options for dropdowns
    publishers = Entry.objects.exclude(
        Q(publisher__isnull=True) | Q(publisher__exact='')
    ).values_list('publisher', flat=True).distinct().order_by('publisher')
    
    ranges = Entry.objects.exclude(
        Q(range__isnull=True) | Q(range__exact='')
    ).values_list('range', flat=True).distinct().order_by('range')
    all_tags = Tag.objects.all()
    
    # Pagination
    paginator = Paginator(entries, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'collection/gallery.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'publisher_filter': publisher_filter,
        'range_filter': range_filter,
        'tag_filter': tag_filter,
        'selected_tags': selected_tags,
        'publishers': publishers,
        'ranges': ranges,
        'all_tags': all_tags,
        'tag_types': tag_types,
    })

@staff_member_required
def edit_image(request, image_id):
    """Edit an existing entry - staff only"""
    # Accept both entry_id and image_id for backwards compatibility
    # Try to get Entry by image_id (which is actually entry_id now)
    entry = get_object_or_404(Entry, id=image_id)
    
    if request.method == 'POST':
        form = EntryEditForm(request.POST, instance=entry)
        if form.is_valid():
            # Save the entry
            updated_entry = form.save()
            
            # Note: Tags are now managed via AJAX in the quick tags section
            # No need to handle tag_type_{id} POST parameters
            
            # Update denormalized fields in all associated images
            entry.images.update(
                name=updated_entry.name,
                publisher=updated_entry.publisher,
                range=updated_entry.range
            )
            
            # Rename files if metadata changed
            for image in entry.images.all():
                if image.image and os.path.exists(image.image.path):
                    old_path = image.image.path
                    _, ext = os.path.splitext(old_path)
                    
                    # Create new filename with UUID
                    publisher = to_camel_case(updated_entry.publisher)
                    range_name = to_camel_case(updated_entry.range)
                    name = to_camel_case(updated_entry.name)
                    unique_id = uuid.uuid4().hex[:8]
                    
                    new_filename = f"{publisher}_{range_name}_{name}_{unique_id}{ext}"
                    new_path = os.path.join(os.path.dirname(old_path), new_filename)
                    
                    # Rename file
                    try:
                        os.rename(old_path, new_path)
                        image.image.name = f"uploaded_images/{new_filename}"
                        image.save()
                    except OSError:
                        pass
            
            messages.success(request, f'Successfully updated "{updated_entry.name}"!')
            return redirect('collection:gallery')
    else:
        form = EntryEditForm(instance=entry)
    
    # Get tag types and all tags for quick tags section
    tag_types = TagType.objects.filter(is_active=True, show_in_gallery=True).order_by('sort_order', 'name')
    all_tags = Tag.objects.select_related('tag_type').prefetch_related('reference_tags').all()
    
    # Handle quick tags filtering
    tag_type_filter = request.GET.get('tag_type', '')
    reference_tag_filter = request.GET.get('reference_tag', '')
    
    quick_tags = all_tags
    selected_tag_type_obj = None
    
    # Filter by tag type
    if tag_type_filter:
        try:
            tag_type_id = int(tag_type_filter)
            quick_tags = quick_tags.filter(tag_type_id=tag_type_id)
            selected_tag_type_obj = TagType.objects.get(id=tag_type_id)
        except (ValueError, TagType.DoesNotExist):
            pass
    
    # Filter by reference tag
    if selected_tag_type_obj and selected_tag_type_obj.reference_tagtypes.exists():
        if reference_tag_filter == 'none':
            quick_tags = quick_tags.filter(reference_tags__isnull=True)
        elif reference_tag_filter:
            try:
                reference_tag_id = int(reference_tag_filter)
                quick_tags = quick_tags.filter(reference_tags__id=reference_tag_id)
            except ValueError:
                pass
    
    # Get reference tags for the filter
    reference_tags = []
    if selected_tag_type_obj and selected_tag_type_obj.reference_tagtypes.exists():
        reference_tags = Tag.objects.filter(
            tag_type__in=selected_tag_type_obj.reference_tagtypes.all()
        ).order_by('name')
    
    return render(request, 'collection/edit.html', {
        'form': form,
        'image': entry,  # Keep 'image' for template compatibility
        'entry': entry,
        'tag_types': tag_types,
        'all_tags': all_tags,
        'quick_tags': quick_tags,
        'tag_type_filter': tag_type_filter,
        'reference_tag_filter': reference_tag_filter,
        'selected_tag_type_obj': selected_tag_type_obj,
        'reference_tags': reference_tags
    })

@staff_member_required
def delete_image(request, image_id):
    """Delete an existing entry and all its images - staff only"""
    # Accept both entry_id and image_id for backwards compatibility
    entry = get_object_or_404(Entry, id=image_id)
    
    if request.method == 'POST':
        entry_name = entry.name
        
        # Delete all associated image files
        for image in entry.images.all():
            if image.image:
                try:
                    if os.path.isfile(image.image.path):
                        os.remove(image.image.path)
                except (ValueError, OSError):
                    pass
        
        # Delete the entry (CASCADE will delete associated images)
        entry.delete()
        
        messages.success(request, f'Successfully deleted "{entry_name}" and all its images!')
        return redirect('collection:gallery')
    
    # For GET requests, show confirmation page
    return render(request, 'collection/delete_confirm.html', {
        'image': entry,  # Keep 'image' for template compatibility
        'entry': entry
    })

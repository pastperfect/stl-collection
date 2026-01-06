from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Tag, TagType
from .forms import TagForm, TagTypeForm
import json

@staff_member_required
def tag_list(request):
    """List all tags - staff only"""
    tags = Tag.objects.all()
    
    # Get all tag types for the filter dropdown
    tag_types = TagType.objects.filter(is_active=True)
    
    # Variables to track selected filters
    selected_tag_type_obj = None
    reference_tags = []
    
    # Apply tag type filter if provided
    tag_type_filter = request.GET.get('tag_type')
    if tag_type_filter:
        if tag_type_filter == 'none':
            # Filter for tags with no tag type
            tags = tags.filter(tag_type__isnull=True)
        else:
            try:
                tag_type_id = int(tag_type_filter)
                tags = tags.filter(tag_type_id=tag_type_id)
                # Get the selected tag type object to check for reference_tagtypes
                selected_tag_type_obj = TagType.objects.filter(id=tag_type_id).first()
                
                # If this tag type has reference_tagtypes, get those tags for the filter
                if selected_tag_type_obj:
                    reference_tagtypes = selected_tag_type_obj.reference_tagtypes.all()
                    if reference_tagtypes.exists():
                        reference_tags = Tag.objects.filter(tag_type__in=reference_tagtypes)
            except (ValueError, TypeError):
                pass  # Invalid filter value, ignore
    
    # Apply reference tag filter if provided
    reference_tag_filter = request.GET.get('reference_tag')
    if reference_tag_filter and reference_tag_filter != 'none':
        try:
            reference_tag_id = int(reference_tag_filter)
            tags = tags.filter(reference_tags__id=reference_tag_id)
        except (ValueError, TypeError):
            pass  # Invalid filter value, ignore
    elif reference_tag_filter == 'none':
        # Filter for tags with no reference tags
        tags = tags.filter(reference_tags__isnull=True)
    
    return render(request, 'tags/list.html', {
        'tags': tags,
        'tag_types': tag_types,
        'selected_tag_type': tag_type_filter,
        'selected_tag_type_obj': selected_tag_type_obj,
        'reference_tags': reference_tags,
        'selected_reference_tag': reference_tag_filter,
        'active_tab': 'tags'
    })

@staff_member_required
def tagtype_list(request):
    """List all tag types - staff only"""
    tagtypes = TagType.objects.all()
    return render(request, 'tags/list.html', {
        'tagtypes': tagtypes,
        'active_tab': 'tagtypes'
    })

@staff_member_required
def create_tag(request):
    """Create a new tag - staff only"""
    # Get the tag type from URL parameter if creating another with same type
    tag_type_id = request.GET.get('tag_type_id')
    
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save()
            messages.success(request, f'Successfully created tag "{tag.name}"!')
            
            # Check which button was clicked
            if 'create_another' in request.POST:
                # Redirect back to create page with the same tag type
                return redirect(f'{request.path}?tag_type_id={tag.tag_type.id}')
            else:
                return redirect('tags:list')
    else:
        # Initialize form with tag type if provided
        initial_data = {}
        if tag_type_id:
            try:
                tag_type = TagType.objects.get(id=tag_type_id)
                initial_data['tag_type'] = tag_type
            except TagType.DoesNotExist:
                pass
        
        form = TagForm(initial=initial_data)
    
    return render(request, 'tags/create.html', {
        'form': form
    })

@staff_member_required
def edit_tag(request, tag_id):
    """Edit an existing tag - staff only"""
    tag = get_object_or_404(Tag, id=tag_id)
    
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(request, f'Successfully updated tag "{tag.name}"!')
            return redirect('tags:list')
    else:
        form = TagForm(instance=tag)
    
    return render(request, 'tags/edit.html', {
        'form': form,
        'tag': tag
    })

@staff_member_required
def delete_tag(request, tag_id):
    """Delete a tag - staff only"""
    tag = get_object_or_404(Tag, id=tag_id)
    
    if request.method == 'POST':
        tag_name = tag.name
        tag.delete()
        messages.success(request, f'Successfully deleted tag "{tag_name}"!')
        return redirect('tags:list')
    
    return render(request, 'tags/delete.html', {
        'tag': tag
    })

@staff_member_required
def create_tagtype(request):
    """Create a new tag type - staff only"""
    if request.method == 'POST':
        form = TagTypeForm(request.POST)
        if form.is_valid():
            tagtype = form.save()
            messages.success(request, f'Successfully created tag type "{tagtype.name}"!')
            return redirect('tags:tagtype_list')
    else:
        form = TagTypeForm()
    
    return render(request, 'tags/create_tagtype.html', {
        'form': form
    })

@staff_member_required
def edit_tagtype(request, tagtype_id):
    """Edit an existing tag type - staff only"""
    tagtype = get_object_or_404(TagType, id=tagtype_id)
    
    if request.method == 'POST':
        form = TagTypeForm(request.POST, instance=tagtype)
        if form.is_valid():
            form.save()
            messages.success(request, f'Successfully updated tag type "{tagtype.name}"!')
            return redirect('tags:tagtype_list')
    else:
        form = TagTypeForm(instance=tagtype)
    
    return render(request, 'tags/edit_tagtype.html', {
        'form': form,
        'tagtype': tagtype
    })

@staff_member_required
def delete_tagtype(request, tagtype_id):
    """Delete a tag type - staff only"""
    tagtype = get_object_or_404(TagType, id=tagtype_id)
    
    if request.method == 'POST':
        tagtype_name = tagtype.name
        # Check if there are tags using this type
        if tagtype.tags.exists():
            messages.error(request, f'Cannot delete tag type "{tagtype_name}" because it is being used by {tagtype.tags.count()} tag(s).')
            return redirect('tags:tagtype_list')
        
        tagtype.delete()
        messages.success(request, f'Successfully deleted tag type "{tagtype_name}"!')
        return redirect('tags:tagtype_list')
    
    return render(request, 'tags/delete_tagtype.html', {
        'tagtype': tagtype
    })

@staff_member_required
def get_reference_tags(request, tagtype_id):
    """API endpoint to get available reference tags for a given tag type, grouped by reference tag type"""
    tagtype = get_object_or_404(TagType, id=tagtype_id)
    
    # Check if this tag type has reference_tagtypes configured
    reference_tagtypes = tagtype.reference_tagtypes.all()
    if not reference_tagtypes.exists():
        return JsonResponse({
            'has_reference': False,
            'reference_tagtypes': []
        })
    
    # Group tags by their tag types
    reference_data = []
    for ref_tagtype in reference_tagtypes:
        tags = Tag.objects.filter(tag_type=ref_tagtype).values('id', 'name')
        reference_data.append({
            'id': ref_tagtype.id,
            'name': ref_tagtype.name,
            'tags': list(tags)
        })
    
    return JsonResponse({
        'has_reference': True,
        'reference_tagtypes': reference_data
    })

@staff_member_required
@require_POST
def update_tagtype_order(request):
    """API endpoint to update tag type sort order via drag and drop"""
    try:
        data = json.loads(request.body)
        order = data.get('order', [])
        
        # Update each tag type's sort_order
        for item in order:
            tagtype_id = item.get('id')
            sort_order = item.get('sort_order')
            
            if tagtype_id and sort_order is not None:
                TagType.objects.filter(id=tagtype_id).update(sort_order=sort_order)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_POST
def toggle_gallery_visibility(request, tagtype_id):
    """API endpoint to toggle tag type visibility in Collection Gallery"""
    try:
        tagtype = get_object_or_404(TagType, id=tagtype_id)
        data = json.loads(request.body)
        show_in_gallery = data.get('show_in_gallery', True)
        
        tagtype.show_in_gallery = show_in_gallery
        tagtype.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_POST
def toggle_upload_visibility(request, tagtype_id):
    """API endpoint to toggle tag type visibility in upload form"""
    try:
        tagtype = get_object_or_404(TagType, id=tagtype_id)
        data = json.loads(request.body)
        set_at_upload = data.get('set_at_upload', False)
        
        tagtype.set_at_upload = set_at_upload
        tagtype.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
def get_available_references(request, tagtype_id):
    """API endpoint to get available tag types for reference selection"""
    try:
        tagtype = get_object_or_404(TagType, id=tagtype_id)
        # Get all tag types except the current one
        available_types = TagType.objects.exclude(id=tagtype_id).values('id', 'name', 'color')
        
        return JsonResponse({
            'success': True,
            'tag_types': list(available_types)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
@require_POST
def update_references(request, tagtype_id):
    """API endpoint to update reference tag types for a tag type"""
    try:
        tagtype = get_object_or_404(TagType, id=tagtype_id)
        data = json.loads(request.body)
        reference_ids = data.get('reference_tagtype_ids', [])
        
        # Clear existing references and set new ones
        tagtype.reference_tagtypes.set(reference_ids)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import EntryUploadForm
from .models import Entry, Image
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

@staff_member_required
def upload_image(request):
    """Upload new entry with one or more images - staff only"""
    if request.method == 'POST':
        form = EntryUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Create the Entry
            entry = form.save()
            
            # Get all uploaded files (supports multiple files)
            uploaded_files = request.FILES.getlist('image')
            
            if not uploaded_files:
                messages.error(request, 'Please select at least one image file.')
                return redirect('image_upload:upload')
            
            # Process each uploaded file
            for index, uploaded_file in enumerate(uploaded_files):
                # Get file extension
                _, ext = os.path.splitext(uploaded_file.name)
                
                # Create filename using camelCase format with UUID
                publisher = to_camel_case(entry.publisher)
                range_name = to_camel_case(entry.range)
                name = to_camel_case(entry.name)
                unique_id = uuid.uuid4().hex[:8]
                
                # Create filename in format: publisher_range_name_uuid.ext
                new_filename = f"{publisher}_{range_name}_{name}_{unique_id}{ext}"
                
                # Create Image instance
                image = Image(
                    entry=entry,
                    name=entry.name,
                    publisher=entry.publisher,
                    range=entry.range,
                    is_primary=(index == 0)  # First image is primary
                )
                
                # Read the file content and save with new name
                file_content = uploaded_file.read()
                image.image.save(new_filename, ContentFile(file_content), save=False)
                
                # Save to database
                image.save()
            
            file_count = len(uploaded_files)
            messages.success(
                request, 
                f'Successfully uploaded "{entry.name}" with {file_count} image{"s" if file_count > 1 else ""}!'
            )
            return redirect('image_upload:upload')
    else:
        form = EntryUploadForm()
    
    # Get the last uploaded entry for auto-fill functionality
    last_entry = Entry.objects.order_by('-upload_date').first()
    
    return render(request, 'image_upload/upload.html', {
        'form': form,
        'last_image': last_entry  # Keep variable name for template compatibility
    })


@staff_member_required
@require_POST
def add_images_to_entry(request, entry_id):
    """AJAX endpoint to add more images to an existing entry"""
    entry = get_object_or_404(Entry, id=entry_id)
    
    # Get uploaded files
    uploaded_files = request.FILES.getlist('images')
    
    if not uploaded_files:
        return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)
    
    added_images = []
    
    # Process each uploaded file
    for uploaded_file in uploaded_files:
        # Get file extension
        _, ext = os.path.splitext(uploaded_file.name)
        
        # Create filename using camelCase format with UUID
        publisher = to_camel_case(entry.publisher)
        range_name = to_camel_case(entry.range)
        name = to_camel_case(entry.name)
        unique_id = uuid.uuid4().hex[:8]
        
        # Create filename in format: publisher_range_name_uuid.ext
        new_filename = f"{publisher}_{range_name}_{name}_{unique_id}{ext}"
        
        # Create Image instance (denormalized metadata from entry)
        image = Image(
            entry=entry,
            name=entry.name,
            publisher=entry.publisher,
            range=entry.range,
            is_primary=False  # Additional images are not primary by default
        )
        
        # Read the file content and save with new name
        file_content = uploaded_file.read()
        image.image.save(new_filename, ContentFile(file_content), save=False)
        
        # Save to database
        image.save()
        
        added_images.append({
            'id': image.id,
            'url': image.image.url,
            'is_primary': image.is_primary
        })
    
    return JsonResponse({
        'success': True,
        'images': added_images,
        'count': len(added_images)
    })


@staff_member_required
@require_POST
def set_primary_image(request, entry_id, image_id):
    """AJAX endpoint to set an image as primary for an entry"""
    entry = get_object_or_404(Entry, id=entry_id)
    image = get_object_or_404(Image, id=image_id, entry=entry)
    
    # Set all images in this entry to not primary
    entry.images.update(is_primary=False)
    
    # Set the selected image as primary
    image.is_primary = True
    image.save()
    
    return JsonResponse({
        'success': True,
        'image_id': image.id
    })


@staff_member_required
@require_POST
def delete_image(request, entry_id, image_id):
    """AJAX endpoint to delete an image from an entry"""
    entry = get_object_or_404(Entry, id=entry_id)
    image = get_object_or_404(Image, id=image_id, entry=entry)
    
    # Check if this is the only image
    image_count = entry.images.count()
    if image_count == 1:
        return JsonResponse({
            'success': False,
            'error': 'Cannot delete the only image in an entry'
        }, status=400)
    
    was_primary = image.is_primary
    
    # Delete the image file and database record
    if image.image:
        image.image.delete()
    image.delete()
    
    # If we deleted the primary image, auto-promote the next oldest
    if was_primary:
        next_image = entry.images.order_by('upload_date').first()
        if next_image:
            next_image.is_primary = True
            next_image.save()
            return JsonResponse({
                'success': True,
                'deleted_id': image_id,
                'new_primary_id': next_image.id
            })
    
    return JsonResponse({
        'success': True,
        'deleted_id': image_id
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_POST
from .forms import (
    EntryUploadForm,
    ALLOWED_PRINT_EXTENSIONS,
    ALLOWED_STL_EXTENSIONS,
    ALLOWED_USER_PRINT_EXTENSIONS,
    validate_file_extension,
    validate_file_size,
)
from .models import Entry, Image, PrintFile, STLFile, UserPrintImage
from tags.models import TagType
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


def validate_uploaded_files(uploaded_files, allowed_extensions):
    for uploaded_file in uploaded_files:
        validate_file_extension(uploaded_file, allowed_extensions)
        validate_file_size(uploaded_file)

@login_required
def upload_image(request):
    """Upload new entry with one or more images"""
    if request.method == 'POST':
        form = EntryUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Validate STL archive files (optional) before saving
            stl_files = request.FILES.getlist('stl_files')
            if stl_files:
                try:
                    validate_uploaded_files(stl_files, ALLOWED_STL_EXTENSIONS)
                except ValidationError as exc:
                    messages.error(request, str(exc))
                    return redirect('image_upload:upload')

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

            # Process STL archive files (optional)
            if stl_files:
                for stl_file in stl_files:
                    STLFile.objects.create(
                        entry=entry,
                        file=stl_file,
                        original_name=stl_file.name,
                        uploaded_by=request.user
                    )
            
            file_count = len(uploaded_files)
            stl_count = len(stl_files)
            stl_message = f" and {stl_count} STL archive{'s' if stl_count != 1 else ''}" if stl_count else ""
            messages.success(
                request,
                f'Successfully uploaded "{entry.name}" with {file_count} image{"s" if file_count > 1 else ""}{stl_message}!'
            )
            return redirect('image_upload:upload')
    else:
        form = EntryUploadForm()
    
    # Get the last uploaded entry for auto-fill functionality
    last_entry = Entry.objects.order_by('-upload_date').first()
    
    # Get TagTypes with set_at_upload=True for grouped display
    upload_tag_types = TagType.objects.filter(
        set_at_upload=True,
        is_active=True
    ).prefetch_related('tags').order_by('sort_order', 'name')
    
    # Get tags from last entry for copy functionality
    last_entry_tags = []
    if last_entry:
        last_entry_tags = list(last_entry.tags.values_list('id', flat=True))
    
    return render(request, 'image_upload/upload.html', {
        'form': form,
        'last_image': last_entry,  # Keep variable name for template compatibility
        'upload_tag_types': upload_tag_types,
        'has_upload_tags': upload_tag_types.exists(),
        'last_entry_tags': last_entry_tags
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
    """Set an image as primary for an entry"""
    entry = get_object_or_404(Entry, id=entry_id)
    image = get_object_or_404(Image, id=image_id, entry=entry)
    
    # Set all images in this entry to not primary
    entry.images.update(is_primary=False)
    
    # Set the selected image as primary
    image.is_primary = True
    image.save()
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'image_id': image.id
        })
    
    # Regular form submission - redirect back to detail page
    from django.shortcuts import redirect
    return redirect('image_details:detail', entry_id=entry_id)


@staff_member_required
@require_POST
def delete_image(request, entry_id, image_id):
    """Delete an image from an entry"""
    entry = get_object_or_404(Entry, id=entry_id)
    image = get_object_or_404(Image, id=image_id, entry=entry)
    
    # Check if this is the only image
    image_count = entry.images.count()
    if image_count == 1:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Cannot delete the only image in an entry'
            }, status=400)
        else:
            from django.contrib import messages
            messages.error(request, 'Cannot delete the only image in an entry')
            from django.shortcuts import redirect
            return redirect('image_details:detail', entry_id=entry_id)
    
    was_primary = image.is_primary
    
    # Delete the image file and database record
    if image.image:
        image.image.delete()
    image.delete()
    
    # If we deleted the primary image, auto-promote the next oldest
    new_primary_id = None
    if was_primary:
        next_image = entry.images.order_by('upload_date').first()
        if next_image:
            next_image.is_primary = True
            next_image.save()
            new_primary_id = next_image.id
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'deleted_id': image_id,
            'new_primary_id': new_primary_id
        })
    
    # Regular form submission - redirect back to detail page
    from django.shortcuts import redirect
    return redirect('image_details:detail', entry_id=entry_id)
    
    return JsonResponse({
        'success': True,
        'deleted_id': image_id
    })


@login_required
@require_POST
def add_stl_files(request, entry_id):
    """AJAX endpoint to add STL archive files to an entry"""
    entry = get_object_or_404(Entry, id=entry_id)
    uploaded_files = request.FILES.getlist('stl_files')

    if not uploaded_files:
        return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)

    try:
        validate_uploaded_files(uploaded_files, ALLOWED_STL_EXTENSIONS)
    except ValidationError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)

    added_files = []
    for uploaded_file in uploaded_files:
        stl_file = STLFile.objects.create(
            entry=entry,
            file=uploaded_file,
            original_name=uploaded_file.name,
            uploaded_by=request.user
        )
        added_files.append({
            'id': stl_file.id,
            'name': stl_file.original_name,
            'url': stl_file.file.url,
            'size': stl_file.file.size,
            'uploaded': stl_file.upload_date.isoformat()
        })

    return JsonResponse({'success': True, 'files': added_files})


@login_required
@require_POST
def add_print_files(request, entry_id):
    """AJAX endpoint to add print files to an entry"""
    entry = get_object_or_404(Entry, id=entry_id)
    uploaded_files = request.FILES.getlist('print_files')

    if not uploaded_files:
        return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)

    try:
        validate_uploaded_files(uploaded_files, ALLOWED_PRINT_EXTENSIONS)
    except ValidationError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)

    added_files = []
    for uploaded_file in uploaded_files:
        print_file = PrintFile.objects.create(
            entry=entry,
            file=uploaded_file,
            original_name=uploaded_file.name,
            uploaded_by=request.user
        )
        added_files.append({
            'id': print_file.id,
            'name': print_file.original_name,
            'url': print_file.file.url,
            'size': print_file.file.size,
            'uploaded': print_file.upload_date.isoformat()
        })

    return JsonResponse({'success': True, 'files': added_files})


@login_required
@require_POST
def add_user_prints(request, entry_id):
    """AJAX endpoint to add user print images to an entry"""
    entry = get_object_or_404(Entry, id=entry_id)
    uploaded_files = request.FILES.getlist('user_prints')

    if not uploaded_files:
        return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)

    try:
        validate_uploaded_files(uploaded_files, ALLOWED_USER_PRINT_EXTENSIONS)
    except ValidationError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)

    added_images = []
    for uploaded_file in uploaded_files:
        user_print = UserPrintImage.objects.create(
            entry=entry,
            image=uploaded_file,
            original_name=uploaded_file.name,
            uploaded_by=request.user
        )
        added_images.append({
            'id': user_print.id,
            'url': user_print.image.url,
            'name': user_print.original_name,
            'uploaded': user_print.upload_date.isoformat()
        })

    return JsonResponse({'success': True, 'images': added_images})


@login_required
@require_POST
def delete_stl_file(request, entry_id, file_id):
    stl_file = get_object_or_404(STLFile, id=file_id, entry_id=entry_id)
    if stl_file.file:
        stl_file.file.delete()
    stl_file.delete()
    return JsonResponse({'success': True, 'deleted_id': file_id})


@login_required
@require_POST
def delete_print_file(request, entry_id, file_id):
    print_file = get_object_or_404(PrintFile, id=file_id, entry_id=entry_id)
    if print_file.file:
        print_file.file.delete()
    print_file.delete()
    return JsonResponse({'success': True, 'deleted_id': file_id})


@login_required
@require_POST
def delete_user_print(request, entry_id, image_id):
    user_print = get_object_or_404(UserPrintImage, id=image_id, entry_id=entry_id)
    if user_print.image:
        user_print.image.delete()
    user_print.delete()
    return JsonResponse({'success': True, 'deleted_id': image_id})


@login_required
def download_stl_file(request, entry_id, file_id):
    stl_file = get_object_or_404(STLFile, id=file_id, entry_id=entry_id)
    response = FileResponse(stl_file.file.open('rb'), as_attachment=True, filename=stl_file.original_name)
    return response


@login_required
def download_print_file(request, entry_id, file_id):
    print_file = get_object_or_404(PrintFile, id=file_id, entry_id=entry_id)
    response = FileResponse(print_file.file.open('rb'), as_attachment=True, filename=print_file.original_name)
    return response

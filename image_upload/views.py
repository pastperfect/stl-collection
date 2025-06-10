from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from .forms import ImageUploadForm
from .models import Image
import os
import re

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
    """Upload a new image - staff only"""
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the form but don't commit to database yet
            image = form.save(commit=False)
            
            # Get the uploaded file
            uploaded_file = request.FILES['image']
            
            # Get file extension
            _, ext = os.path.splitext(uploaded_file.name)
            
            # Create new filename using camelCase format
            publisher = to_camel_case(image.publisher)
            range_name = to_camel_case(image.range)
            name = to_camel_case(image.name)
            
            # Create filename in format: publisher_range_name_initial.ext
            new_filename = f"{publisher}_{range_name}_{name}_initial{ext}"
            
            # Read the file content and save with new name
            file_content = uploaded_file.read()
            image.image.save(new_filename, ContentFile(file_content), save=False)
            
            # Now save to database
            image.save()
            
            # Save many-to-many relationships
            form.save_m2m()
            
            messages.success(request, f'Successfully uploaded "{image.name}" as "{new_filename}"!')
            return redirect('image_upload:upload')
    else:
        form = ImageUploadForm()
    
    # Get the last uploaded image for auto-fill functionality
    last_image = Image.objects.order_by('-upload_date').first()
    
    return render(request, 'image_upload/upload.html', {
        'form': form,
        'last_image': last_image
    })

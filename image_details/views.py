from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from image_upload.models import Image

@login_required
def image_detail(request, image_id):
    """Show detailed view of an image"""
    image = get_object_or_404(Image, id=image_id)
    
    # Get related images (same publisher or range, excluding current image)
    related_images = Image.objects.filter(
        Q(publisher=image.publisher) | Q(range=image.range)
    ).exclude(id=image.id)[:6]
    
    return render(request, 'image_details/detail.html', {
        'image': image,
        'related_images': related_images
    })

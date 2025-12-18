from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from image_upload.models import Entry, Image

@login_required
def image_detail(request, entry_id):
    """Show detailed view of an entry with all its images"""
    entry = get_object_or_404(Entry, id=entry_id)
    
    # Get all images for this entry, ordered by primary first, then upload date
    images = entry.images.all()
    
    # Get related entries (same publisher or range, excluding current entry)
    related_entries = Entry.objects.filter(
        Q(publisher=entry.publisher) | Q(range=entry.range)
    ).exclude(id=entry.id)[:6]
    
    return render(request, 'image_details/detail.html', {
        'entry': entry,
        'image': entry.get_display_image(),  # For backward compatibility
        'images': images,
        'related_images': related_entries
    })

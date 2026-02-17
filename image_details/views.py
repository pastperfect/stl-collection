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

    user_prints = entry.user_prints.all()
    stl_files = entry.stl_files.all()
    print_files = entry.print_files.all()
    
    return render(request, 'image_details/detail.html', {
        'entry': entry,
        'image': entry.get_display_image(),  # For backward compatibility
        'images': images,
        'related_images': related_entries,
        'user_prints': user_prints,
        'stl_files': stl_files,
        'print_files': print_files
    })

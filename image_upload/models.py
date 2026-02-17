import os
import uuid
from django.conf import settings
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.text import get_valid_filename, slugify
from tags.models import Tag


def _safe_entry_segment(value, fallback):
    safe_value = slugify(value or "")
    return safe_value if safe_value else fallback


@deconstructible
class EntryUploadPath:
    def __init__(self, root_folder):
        self.root_folder = root_folder

    def __call__(self, instance, filename):
        entry = instance.entry
        publisher = _safe_entry_segment(getattr(entry, "publisher", None), "unknown-publisher")
        range_name = _safe_entry_segment(getattr(entry, "range", None), "unknown-range")
        name = _safe_entry_segment(getattr(entry, "name", None), "unknown-name")

        safe_filename = get_valid_filename(filename)
        stem, ext = os.path.splitext(safe_filename)
        stem = slugify(stem) or "file"
        unique_id = uuid.uuid4().hex[:8]

        return f"{self.root_folder}/{publisher}/{range_name}/{name}/{stem}_{unique_id}{ext.lower()}"


class Entry(models.Model):
    """
    Represents a collection entry that can have multiple images.
    """
    # Basic information
    name = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    range = models.CharField(max_length=255, blank=True, null=True)
    folder_location = models.CharField(max_length=500, blank=True, null=True)
    
    # Metadata
    upload_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    # Many-to-many relationship with tags
    tags = models.ManyToManyField(Tag, blank=True)
    
    class Meta:
        ordering = ['-upload_date']
        verbose_name_plural = 'Entries'
    
    def __str__(self):
        return self.name
    
    def get_display_image(self):
        """
        Returns the primary image, or the first uploaded image if no primary is set.
        """
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary
        return self.images.order_by('upload_date').first()


class Image(models.Model):
    """
    Represents a single image file associated with an Entry.
    """
    # Relationship to Entry (nullable during migration)
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    
    # File field for image files
    image = models.ImageField(upload_to='uploaded_images/')
    
    # Denormalized fields for filename generation (copied from Entry)
    name = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    range = models.CharField(max_length=255, blank=True, null=True)
    
    # Image-specific metadata
    is_primary = models.BooleanField(default=False)
    upload_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'upload_date']
    
    def __str__(self):
        return f"{self.entry.name} - Image {self.id}"


class STLFile(models.Model):
    """Represents an STL archive file associated with an Entry."""
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name='stl_files')
    file = models.FileField(upload_to=EntryUploadPath('stlFiles'), max_length=255)
    original_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_stl_files'
    )
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.entry.name} - STL {self.original_name}"


class PrintFile(models.Model):
    """Represents a print file associated with an Entry."""
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name='print_files')
    file = models.FileField(upload_to=EntryUploadPath('printFiles'), max_length=255)
    original_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_print_files'
    )
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.entry.name} - Print {self.original_name}"


class UserPrintImage(models.Model):
    """Represents a user-submitted print image associated with an Entry."""
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name='user_prints')
    image = models.ImageField(upload_to=EntryUploadPath('userPrints'), max_length=255)
    original_name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_user_prints'
    )
    upload_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return f"{self.entry.name} - User Print {self.original_name}"

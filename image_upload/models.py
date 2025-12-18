from django.db import models
from tags.models import Tag


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

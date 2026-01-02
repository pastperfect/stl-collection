from django.db import models
from django.core.exceptions import ValidationError

class TagType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, help_text="Optional description of this tag type")
    color = models.CharField(max_length=7, default='#6c757d', help_text="Hex color code for display (e.g., #FF5733)")
    reference_tagtype = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referencing_tagtypes',
        help_text="Optional: Allow tags of this type to reference tags from another type"
    )
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    is_active = models.BooleanField(default=True, help_text="Inactive types won't appear in filters")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = "Tag Type"
        verbose_name_plural = "Tag Types"
        constraints = [
            models.CheckConstraint(
                check=~models.Q(reference_tagtype=models.F('id')),
                name='tagtype_no_self_reference'
            )
        ]
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tag_type = models.ForeignKey(TagType, on_delete=models.CASCADE, related_name='tags', null=True, blank=True)
    reference_tag = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referenced_by',
        help_text="Optional: Reference a tag from the type specified by this tag's TagType"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['tag_type__sort_order', 'tag_type__name', 'name']
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate that reference_tag matches the allowed reference_tagtype"""
        super().clean()
        
        # Prevent self-referencing
        if self.reference_tag and self.pk and self.reference_tag.pk == self.pk:
            raise ValidationError({'reference_tag': 'A tag cannot reference itself.'})
        
        # Only allow reference_tag if tag_type has a reference_tagtype configured
        if self.reference_tag:
            if not self.tag_type:
                raise ValidationError({
                    'reference_tag': 'Cannot set a reference tag without a tag type.'
                })
            
            if not self.tag_type.reference_tagtype:
                raise ValidationError({
                    'reference_tag': f'The tag type "{self.tag_type}" does not allow tag references. '
                                   f'Configure a reference tag type first.'
                })
            
            # Validate that reference_tag belongs to the correct TagType
            if self.reference_tag.tag_type != self.tag_type.reference_tagtype:
                raise ValidationError({
                    'reference_tag': f'Reference tag must be of type "{self.tag_type.reference_tagtype}". '
                                   f'Selected tag is of type "{self.reference_tag.tag_type or "None"}".'
                })
    
    def get_color(self):
        """Return the tag type color, or default gray if no tag type"""
        return self.tag_type.color if self.tag_type else '#6c757d'
    
    def get_text_color(self):
        """Return appropriate text color (white or black) based on background color"""
        if not self.tag_type:
            return 'white'
        
        # Convert hex to RGB
        hex_color = self.tag_type.color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Calculate brightness
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        
        # Return black for light colors, white for dark colors
        return 'black' if brightness > 128 else 'white'

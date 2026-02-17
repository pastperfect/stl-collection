import os
from django import forms
from django.conf import settings
from .models import Entry, Image
from tags.models import Tag

ALLOWED_STL_EXTENSIONS = {'.zip', '.7z', '.rar'}
ALLOWED_PRINT_EXTENSIONS = {'.pwsz', '.pwscene'}
ALLOWED_USER_PRINT_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def validate_file_extension(uploaded_file, allowed_extensions):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in allowed_extensions:
        raise forms.ValidationError(
            f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(allowed_extensions))}."
        )


def validate_file_size(uploaded_file):
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', None)
    if max_size and uploaded_file.size > max_size:
        raise forms.ValidationError(
            f"File exceeds max size of {max_size // (1024 * 1024)} MB."
        )


class EntryUploadForm(forms.ModelForm):
    """Form for creating new entries with multiple images."""
    # Note: multiple file upload handled in view via request.FILES.getlist()
    # The 'multiple' attribute is added via JavaScript in the template
    
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to only tags from TagTypes with set_at_upload=True
        from tags.models import TagType
        self.fields['tags'].queryset = Tag.objects.filter(
            tag_type__set_at_upload=True,
            tag_type__is_active=True
        ).select_related('tag_type').order_by(
            'tag_type__sort_order',
            'tag_type__name',
            'name'
        )
    
    class Meta:
        model = Entry
        fields = ['name', 'publisher', 'range', 'folder_location', 'notes', 'tags']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'range': forms.TextInput(attrs={'class': 'form-control'}),
            'folder_location': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class EntryEditForm(forms.ModelForm):
    """Form for editing entry metadata."""
    
    class Meta:
        model = Entry
        fields = ['name', 'publisher', 'range', 'folder_location', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'range': forms.TextInput(attrs={'class': 'form-control'}),
            'folder_location': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
        }

# Keep old forms for backward compatibility during migration
class ImageUploadForm(forms.ModelForm):
    """Legacy form - use EntryUploadForm instead."""
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        required=False
    )
    
    class Meta:
        model = Image
        fields = ['image', 'name', 'publisher', 'range']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'range': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'})
        }

class ImageEditForm(forms.ModelForm):
    """Legacy form - use EntryEditForm instead."""
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'data-live-search': 'true',
            'multiple': True
        }),
        required=False
    )
    
    class Meta:
        model = Image
        fields = ['name', 'publisher', 'range']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'range': forms.TextInput(attrs={'class': 'form-control'})
        }

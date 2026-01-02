from django import forms
from .models import Entry, Image
from tags.models import Tag

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

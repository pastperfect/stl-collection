from django import forms
from .models import Tag, TagType
from .widgets import ColorPickerWidget

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'tag_type', 'reference_tag']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tag_type': forms.Select(attrs={'class': 'form-select'}),
            'reference_tag': forms.Select(attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active tag types
        self.fields['tag_type'].queryset = TagType.objects.filter(is_active=True)
        
        # Add help text
        self.fields['reference_tag'].help_text = "Optional: Reference a tag from the allowed type"
        
        # Filter reference_tag queryset based on the tag_type's reference_tagtype
        if self.instance.pk and self.instance.tag_type and self.instance.tag_type.reference_tagtype:
            # Editing existing tag - filter to tags of the reference_tagtype
            self.fields['reference_tag'].queryset = Tag.objects.filter(
                tag_type=self.instance.tag_type.reference_tagtype
            ).exclude(pk=self.instance.pk)
        elif self.data.get('tag_type'):
            # Form submission with tag_type selected
            try:
                tag_type_id = int(self.data.get('tag_type'))
                tag_type = TagType.objects.get(pk=tag_type_id)
                if tag_type.reference_tagtype:
                    self.fields['reference_tag'].queryset = Tag.objects.filter(
                        tag_type=tag_type.reference_tagtype
                    )
                else:
                    self.fields['reference_tag'].queryset = Tag.objects.none()
            except (ValueError, TypeError, TagType.DoesNotExist):
                self.fields['reference_tag'].queryset = Tag.objects.none()
        else:
            # No tag_type selected yet
            self.fields['reference_tag'].queryset = Tag.objects.none()
    
    def clean_reference_tag(self):
        """Validate that reference_tag is only set when tag_type has reference_tagtype configured"""
        reference_tag = self.cleaned_data.get('reference_tag')
        tag_type = self.cleaned_data.get('tag_type')
        
        if reference_tag:
            if not tag_type:
                raise forms.ValidationError('Cannot set a reference tag without selecting a tag type.')
            
            if not tag_type.reference_tagtype:
                raise forms.ValidationError(
                    f'The tag type "{tag_type}" does not allow tag references. '
                    f'Configure a reference tag type first in the Tag Types settings.'
                )
            
            # Validate that reference_tag belongs to the correct TagType
            if reference_tag.tag_type != tag_type.reference_tagtype:
                raise forms.ValidationError(
                    f'Reference tag must be of type "{tag_type.reference_tagtype}". '
                    f'Selected tag is of type "{reference_tag.tag_type or "None"}".'
                )
        
        return reference_tag

class TagTypeForm(forms.ModelForm):
    class Meta:
        model = TagType
        fields = ['name', 'description', 'color', 'reference_tagtype', 'sort_order', 'is_active', 'show_in_gallery', 'set_at_upload']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Fantasy, Sci-Fi, Terrain'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Optional description of this tag type...'
            }),
            'color': ColorPickerWidget(),
            'reference_tagtype': forms.Select(attrs={
                'class': 'form-select'
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'value': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'show_in_gallery': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'set_at_upload': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].help_text = "A descriptive name for this tag category"
        self.fields['description'].help_text = "Optional description explaining what tags of this type represent"
        self.fields['color'].help_text = "Color used to display tags of this type (click to open color picker)"
        self.fields['reference_tagtype'].help_text = "Optional: Allow tags of this type to reference tags from another tag type (e.g., GW Alternative → Faction)"
        self.fields['sort_order'].help_text = "Lower numbers appear first in lists (0 = first)"
        self.fields['is_active'].help_text = "Inactive types won't appear in tag creation forms"
        self.fields['show_in_gallery'].help_text = "Display this tag type as a filter in the Collection Gallery"
        self.fields['set_at_upload'].help_text = "Allow users to select tags of this type when uploading new items"
        
        # Exclude self from reference_tagtype dropdown when editing
        if self.instance.pk:
            self.fields['reference_tagtype'].queryset = TagType.objects.exclude(pk=self.instance.pk)
        else:
            self.fields['reference_tagtype'].queryset = TagType.objects.all()

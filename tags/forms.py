from django import forms
from .models import Tag, TagType
from .widgets import ColorPickerWidget

class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'tag_type', 'reference_tags']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tag_type': forms.Select(attrs={'class': 'form-select'}),
            'reference_tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active tag types
        self.fields['tag_type'].queryset = TagType.objects.filter(is_active=True)
        
        # Add help text
        self.fields['reference_tags'].help_text = "Optional: Reference tags from the allowed types"
        
        # Filter reference_tags queryset based on the tag_type's reference_tagtypes
        if self.instance.pk and self.instance.tag_type:
            reference_tagtypes = self.instance.tag_type.reference_tagtypes.all()
            if reference_tagtypes.exists():
                # Editing existing tag - filter to tags of the reference_tagtypes
                self.fields['reference_tags'].queryset = Tag.objects.filter(
                    tag_type__in=reference_tagtypes
                ).exclude(pk=self.instance.pk)
            else:
                self.fields['reference_tags'].queryset = Tag.objects.none()
        elif self.data.get('tag_type'):
            # Form submission with tag_type selected
            try:
                tag_type_id = int(self.data.get('tag_type'))
                tag_type = TagType.objects.get(pk=tag_type_id)
                reference_tagtypes = tag_type.reference_tagtypes.all()
                if reference_tagtypes.exists():
                    self.fields['reference_tags'].queryset = Tag.objects.filter(
                        tag_type__in=reference_tagtypes
                    )
                else:
                    self.fields['reference_tags'].queryset = Tag.objects.none()
            except (ValueError, TypeError, TagType.DoesNotExist):
                self.fields['reference_tags'].queryset = Tag.objects.none()
        else:
            # No tag_type selected yet
            self.fields['reference_tags'].queryset = Tag.objects.none()
    
    def clean_reference_tags(self):
        """Validate that reference_tags are only set when tag_type has reference_tagtypes configured"""
        reference_tags = self.cleaned_data.get('reference_tags')
        tag_type = self.cleaned_data.get('tag_type')
        
        if reference_tags:
            if not tag_type:
                raise forms.ValidationError('Cannot set reference tags without selecting a tag type.')
            
            reference_tagtypes = tag_type.reference_tagtypes.all()
            if not reference_tagtypes.exists():
                raise forms.ValidationError(
                    f'The tag type "{tag_type}" does not allow tag references. '
                    f'Configure reference tag types first in the Tag Types settings.'
                )
            
            # Validate that all reference_tags belong to allowed TagTypes
            allowed_type_ids = list(reference_tagtypes.values_list('id', flat=True))
            for ref_tag in reference_tags:
                if ref_tag.tag_type_id not in allowed_type_ids:
                    raise forms.ValidationError(
                        f'Reference tag "{ref_tag.name}" is of type "{ref_tag.tag_type or "None"}", '
                        f'which is not in the allowed reference types for "{tag_type}".'
                    )
        
        return reference_tags

class TagTypeForm(forms.ModelForm):
    class Meta:
        model = TagType
        fields = ['name', 'description', 'color', 'reference_tagtypes', 'sort_order', 'is_active', 'show_in_gallery', 'set_at_upload']
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
            'reference_tagtypes': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '5'
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
        self.fields['reference_tagtypes'].help_text = "Optional: Allow tags of this type to reference tags from other tag types (e.g., GW Alternative → Faction, Army). Hold Ctrl/Cmd to select multiple."
        self.fields['sort_order'].help_text = "Lower numbers appear first in lists (0 = first)"
        self.fields['is_active'].help_text = "Inactive types won't appear in tag creation forms"
        self.fields['show_in_gallery'].help_text = "Display this tag type as a filter in the Collection Gallery"
        self.fields['set_at_upload'].help_text = "Allow users to select tags of this type when uploading new items"
        
        # Exclude self from reference_tagtypes dropdown when editing
        if self.instance.pk:
            self.fields['reference_tagtypes'].queryset = TagType.objects.exclude(pk=self.instance.pk)
        else:
            self.fields['reference_tagtypes'].queryset = TagType.objects.all()

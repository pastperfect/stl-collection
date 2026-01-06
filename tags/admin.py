from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import Tag, TagType
from .widgets import ColorPickerWidget

@admin.register(TagType)
class TagTypeAdmin(ModelAdmin):
    list_display = ['name', 'color_preview', 'reference_tagtype', 'sort_order', 'is_active', 'show_in_gallery', 'set_at_upload', 'tag_count', 'created_at']
    list_filter = ['is_active', 'created_at', 'reference_tagtype']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['sort_order', 'is_active', 'show_in_gallery', 'set_at_upload']
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['color'].widget = ColorPickerWidget()
        return form
    
    def color_preview(self, obj):
        return format_html(
            '<div style="display: inline-flex; align-items: center; gap: 8px;">'
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; border-radius: 4px;"></div>'
            '<span>{}</span>'
            '</div>',
            obj.color,
            obj.color
        )
    color_preview.short_description = 'Color'
    color_preview.admin_order_field = 'color'
    
    def tag_count(self, obj):
        return obj.tags.count()
    tag_count.short_description = 'Tags'

@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ['name', 'tag_type', 'reference_tag', 'usage_count', 'created_at']
    list_filter = ['tag_type', 'created_at', 'reference_tag']
    search_fields = ['name']
    ordering = ['tag_type__sort_order', 'tag_type__name', 'name']
    
    def usage_count(self, obj):
        return obj.image_set.count()
    usage_count.short_description = 'Usage Count'

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import Tag, TagType
from .widgets import ColorPickerWidget

@admin.register(TagType)
class TagTypeAdmin(ModelAdmin):
    list_display = ['name', 'color_preview', 'reference_tagtypes_display', 'sort_order', 'is_active', 'show_in_gallery', 'set_at_upload', 'tag_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['sort_order', 'is_active', 'show_in_gallery', 'set_at_upload']
    filter_horizontal = ['reference_tagtypes']
    
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
    
    def reference_tagtypes_display(self, obj):
        ref_types = obj.reference_tagtypes.all()
        if ref_types.exists():
            return ', '.join([rt.name for rt in ref_types])
        return '-'
    reference_tagtypes_display.short_description = 'Reference Tag Types'
    
    def tag_count(self, obj):
        return obj.tags.count()
    tag_count.short_description = 'Tags'

@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ['name', 'tag_type', 'reference_tags_display', 'usage_count', 'created_at']
    list_filter = ['tag_type', 'created_at']
    search_fields = ['name']
    ordering = ['tag_type__sort_order', 'tag_type__name', 'name']
    filter_horizontal = ['reference_tags']
    
    def reference_tags_display(self, obj):
        ref_tags = obj.reference_tags.all()
        if ref_tags.exists():
            return ', '.join([f"{rt.name} ({rt.tag_type})" for rt in ref_tags])
        return '-'
    reference_tags_display.short_description = 'Reference Tags'
    
    def usage_count(self, obj):
        return obj.entry_set.count()
    usage_count.short_description = 'Usage Count'

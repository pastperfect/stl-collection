from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Entry, Image

@admin.register(Entry)
class EntryAdmin(ModelAdmin):
    list_display = ['name', 'publisher', 'range', 'upload_date']
    list_filter = ['publisher', 'range', 'upload_date', 'tags']
    search_fields = ['name', 'publisher', 'range', 'notes']
    filter_horizontal = ['tags']
    ordering = ['-upload_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name',)
        }),
        ('Metadata', {
            'fields': ('publisher', 'range', 'folder_location')
        }),
        ('Additional Information', {
            'fields': ('notes', 'tags')
        }),
    )

class ImageInline(admin.TabularInline):
    model = Image
    extra = 0
    fields = ['image', 'name', 'publisher', 'range', 'is_primary', 'upload_date']
    readonly_fields = ['upload_date']

@admin.register(Image)
class ImageAdmin(ModelAdmin):
    list_display = ['__str__', 'entry', 'is_primary', 'upload_date']
    list_filter = ['is_primary', 'upload_date', 'entry__publisher', 'entry__range']
    search_fields = ['entry__name', 'entry__publisher', 'entry__range']
    ordering = ['-upload_date']
    
    fieldsets = (
        ('Entry Association', {
            'fields': ('entry',)
        }),
        ('File Information', {
            'fields': ('image', 'is_primary')
        }),
        ('Denormalized Metadata', {
            'fields': ('name', 'publisher', 'range'),
            'description': 'These fields are copied from the Entry for filename generation.'
        }),
    )

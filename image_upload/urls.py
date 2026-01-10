from django.urls import path
from . import views
from . import api_views

app_name = 'image_upload'

urlpatterns = [
    path('upload/', views.upload_image, name='upload'),
    path('entry/<int:entry_id>/add-images/', views.add_images_to_entry, name='add_images'),
    path('entry/<int:entry_id>/image/<int:image_id>/set-primary/', views.set_primary_image, name='set_primary'),
    path('entry/<int:entry_id>/image/<int:image_id>/delete/', views.delete_image, name='delete_image'),
    
    # API endpoints for bulk import
    path('api/health/', api_views.api_health, name='api_health'),
    path('api/check-duplicate/', api_views.api_check_duplicate, name='api_check_duplicate'),
    path('api/get-tags/', api_views.api_get_tags, name='api_get_tags'),
    path('api/create-entry/', api_views.api_create_entry, name='api_create_entry'),
    path('api/upload-image/', api_views.api_upload_image, name='api_upload_image'),
]

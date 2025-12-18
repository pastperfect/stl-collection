from django.urls import path
from . import views

app_name = 'image_upload'

urlpatterns = [
    path('upload/', views.upload_image, name='upload'),
    path('entry/<int:entry_id>/add-images/', views.add_images_to_entry, name='add_images'),
    path('entry/<int:entry_id>/image/<int:image_id>/set-primary/', views.set_primary_image, name='set_primary'),
    path('entry/<int:entry_id>/image/<int:image_id>/delete/', views.delete_image, name='delete_image'),
]

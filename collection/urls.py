from django.urls import path
from . import views

app_name = 'collection'

urlpatterns = [
    path('', views.gallery, name='gallery'),
    path('edit/<int:image_id>/', views.edit_image, name='edit'),
    path('delete/<int:image_id>/', views.delete_image, name='delete'),
    path('bulk-delete/', views.bulk_delete, name='bulk_delete'),
]

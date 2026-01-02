from django.urls import path
from . import views

app_name = 'tags'

urlpatterns = [
    path('', views.tag_list, name='list'),
    path('types/', views.tagtype_list, name='tagtype_list'),
    path('create/', views.create_tag, name='create'),
    path('edit/<int:tag_id>/', views.edit_tag, name='edit'),
    path('delete/<int:tag_id>/', views.delete_tag, name='delete'),
    # TagType URLs
    path('tagtype/create/', views.create_tagtype, name='create_tagtype'),
    path('tagtype/edit/<int:tagtype_id>/', views.edit_tagtype, name='edit_tagtype'),
    path('tagtype/delete/<int:tagtype_id>/', views.delete_tagtype, name='delete_tagtype'),
    # API endpoints
    path('api/reference-tags/<int:tagtype_id>/', views.get_reference_tags, name='api_reference_tags'),
    path('api/tagtype/update-order/', views.update_tagtype_order, name='update_tagtype_order'),
    path('api/tagtype/<int:tagtype_id>/toggle-gallery/', views.toggle_gallery_visibility, name='toggle_gallery_visibility'),
]

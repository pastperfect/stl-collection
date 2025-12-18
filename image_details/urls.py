from django.urls import path
from . import views

app_name = 'image_details'

urlpatterns = [
    path('<int:entry_id>/', views.image_detail, name='detail'),
]

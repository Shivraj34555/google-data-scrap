from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('scrape', views.scrape_data, name='scrape'),
    path('status/<str:task_id>', views.get_status, name='status'),
    path('download/<str:task_id>', views.download_file, name='download'),
]

# projects/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('upload/', views.upload_ifc, name='upload_ifc'),
]
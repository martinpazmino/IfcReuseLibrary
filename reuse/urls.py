from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    path('upload/', views.upload_ifc_to_fastapi, name='upload_page'),
    path('catalog/', views.catalog, name='catalog'),
    path('api/', views.api_view, name='api'),
    path('about/', views.about, name='about'),
    path('projects/', views.project_list, name='project_list'),  # ← added from projects/urls.py
]

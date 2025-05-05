from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    path('upload/',views.upload_page, name='upload_page'),  # ← render the HTML form here
    path('catalog/', views.catalog, name='catalog'),
    path('api/', views.api_view, name='api'),
    path('about/', views.about, name='about'),


]

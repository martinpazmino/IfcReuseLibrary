# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('upload_profile_image/', views.upload_profile_image, name='upload_profile_image'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('register/', views.register, name='register'),



]
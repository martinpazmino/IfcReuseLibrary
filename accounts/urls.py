# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('token/', views.generate_token, name='generate_token'),
    path('login/', views.user_login, name='login'),
]
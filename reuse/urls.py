from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    path('upload/', views.upload_ifc_to_fastapi, name='upload_page'),
    path('catalog/', views.catalog, name='catalog'),
    path('api/', views.api_view, name='api'),
    path('about/', views.about, name='about'),
    path('projects/', views.project_list, name='project_list'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/settings/'
    ), name='password_change'),

]

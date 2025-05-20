from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reuse.urls')),             # Main UI
    path('accounts/', include('accounts.urls')), # User accounts
]

# Serve static and media files in development only
if settings.DEBUG:
    # Serve static files from STATICFILES_DIRS
    for static_dir in settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=static_dir)
    # Serve media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
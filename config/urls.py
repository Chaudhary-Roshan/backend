from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.static import serve

urlpatterns = [
    path('', lambda req: redirect('admin/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


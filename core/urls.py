from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('estoque.urls')),
]

# Esta lógica é vital: ela diz ao Django para servir os arquivos da pasta MEDIA_ROOT
# sempre que a URL começar com MEDIA_URL (ex: /media/)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
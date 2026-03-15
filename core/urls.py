from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('estoque.urls')), # O seu app de estoque
]

# NOVO: Só adiciona essa rota de arquivos se o sistema estiver em modo de Desenvolvimento (DEBUG)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
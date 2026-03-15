from django.contrib import admin
from .models import Fornecedor, TipoAco, MTC, Bobina, TipoConsumo, Consumo, Perfil

admin.site.register(Fornecedor)
admin.site.register(TipoAco)
admin.site.register(MTC)
admin.site.register(Bobina)
admin.site.register(TipoConsumo)
admin.site.register(Consumo)
admin.site.register(Perfil) # Liberando a troca de perfil para os ADMs
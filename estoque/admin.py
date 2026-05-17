from django.contrib import admin
# 🟢 Não esqueça de adicionar o RelatorioDivergenciaIA no final do import abaixo!
from .models import Fornecedor, TipoAco, MTC, Bobina, TipoConsumo, Consumo, Perfil, RelatorioDivergenciaIA

# --- Seus registros originais (Modo Simples) ---
admin.site.register(Fornecedor)
admin.site.register(TipoAco)
admin.site.register(MTC)
admin.site.register(Bobina)
admin.site.register(TipoConsumo)
admin.site.register(Consumo)
admin.site.register(Perfil) # Liberando a troca de perfil para os ADMs

# --- Novo registro do Relatório de IA (Modo Customizado) ---
@admin.register(RelatorioDivergenciaIA)
class RelatorioDivergenciaIAAdmin(admin.ModelAdmin):
    # Quais colunas aparecem na lista
    list_display = ('numero_mtc', 'usuario', 'data_reporte', 'status')
    # Filtros na barra lateral direita
    list_filter = ('status', 'data_reporte')
    # Cria uma barra de pesquisa que busca por NF ou texto do erro
    search_fields = ('numero_mtc', 'detalhes_erro')
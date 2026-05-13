from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('tipo-aco/<int:tipo_id>/', views.detalhe_tipo_aco, name='detalhe_tipo'),
    
    # ROTAS DE FORNECEDOR
    path('fornecedores/', views.lista_fornecedores, name='lista_fornecedores'),
    path('fornecedor/novo/', views.cadastrar_fornecedor, name='cadastrar_fornecedor'),
    path('fornecedor/<int:id>/editar/', views.editar_fornecedor, name='editar_fornecedor'),
    path('fornecedor/<int:id>/excluir/', views.excluir_fornecedor, name='excluir_fornecedor'),
    
    # ROTAS DE TIPO DE AÇO
    path('tipos-aco/', views.lista_tipos_aco, name='lista_tipos_aco'),
    path('tipo-aco/novo/', views.cadastrar_tipo_aco, name='cadastrar_tipo_aco'),
    path('tipo-aco/<int:id>/editar/', views.editar_tipo_aco, name='editar_tipo_aco'),
    path('tipo-aco/<int:id>/excluir/', views.excluir_tipo_aco, name='excluir_tipo_aco'),
    
    # ROTAS DE TIPO DE CONSUMO
    path('tipos-consumo/', views.lista_tipos_consumo, name='lista_tipos_consumo'),
    path('tipo-consumo/novo/', views.cadastrar_tipo_consumo, name='cadastrar_tipo_consumo'),
    path('tipo-consumo/<int:id>/editar/', views.editar_tipo_consumo, name='editar_tipo_consumo'),
    path('tipo-consumo/<int:id>/excluir/', views.excluir_tipo_consumo, name='excluir_tipo_consumo'),

    # NÚCLEO (MTC E CONSUMO)
    path('lote/novo/', views.cadastrar_lote_mtc, name='cadastrar_lote_mtc'),
    path('lote/<int:mtc_id>/editar/', views.editar_lote_mtc, name='editar_lote_mtc'),
    path('lote/<int:mtc_id>/excluir/', views.excluir_lote_mtc, name='excluir_lote_mtc'),
    
    path('consumo/novo/', views.registrar_consumo, name='registrar_consumo'),
    path('consumo/<int:consumo_id>/editar/', views.editar_consumo, name='editar_consumo'),
    path('consumo/<int:consumo_id>/excluir/', views.excluir_consumo, name='excluir_consumo'),
    
    path('auditoria/', views.relatorio_auditoria, name='relatorio_auditoria'),
    path('relatorios/estoque-atual/', views.relatorio_estoque_atual, name='relatorio_estoque_atual'),
    path('relatorios/todas-bobinas/', views.relatorio_todas_bobinas, name='relatorio_todas_bobinas'),
    
    path('login/', auth_views.LoginView.as_view(template_name='estoque/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('bobina/<int:bobina_id>/etiqueta/', views.imprimir_etiqueta, name='imprimir_etiqueta'),
]
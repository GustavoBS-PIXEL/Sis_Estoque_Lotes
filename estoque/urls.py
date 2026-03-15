from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('tipo-aco/<int:tipo_id>/', views.detalhe_tipo_aco, name='detalhe_tipo'),
    path('fornecedor/novo/', views.cadastrar_fornecedor, name='cadastrar_fornecedor'),
    path('fornecedores/', views.lista_fornecedores, name='lista_fornecedores'),
    
    path('lote/novo/', views.cadastrar_lote_mtc, name='cadastrar_lote_mtc'),
    
    # NOVAS ROTAS DE EDIÇÃO E EXCLUSÃO DO MTC
    path('lote/<int:mtc_id>/editar/', views.editar_lote_mtc, name='editar_lote_mtc'),
    path('lote/<int:mtc_id>/excluir/', views.excluir_lote_mtc, name='excluir_lote_mtc'),
    
    path('consumo/novo/', views.registrar_consumo, name='registrar_consumo'),
    path('consumo/<int:consumo_id>/editar/', views.editar_consumo, name='editar_consumo'),
    path('consumo/<int:consumo_id>/excluir/', views.excluir_consumo, name='excluir_consumo'),
    
    path('auditoria/', views.relatorio_auditoria, name='relatorio_auditoria'),
    
    path('login/', auth_views.LoginView.as_view(template_name='estoque/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
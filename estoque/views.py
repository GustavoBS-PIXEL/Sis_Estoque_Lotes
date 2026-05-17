# --- IMPORTS DO DJANGO ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.db.models import F
from django.urls import reverse
from django.contrib import messages

# --- IMPORTS DO SEU PROJETO ---
from .models import TipoAco, Bobina, Fornecedor, Consumo, RegistroAuditoria, MTC, TipoConsumo, Bobina, RelatorioDivergenciaIA
from .forms import FornecedorForm, BobinaFormSet, ConsumoForm, MTCForm, TipoAcoForm, TipoConsumoForm

# --- IMPORTS DE UTILITÁRIOS (QR Code, Matemática, etc) ---
import math
import qrcode
from io import BytesIO
import base64
import os
import json
from dotenv import load_dotenv

# --- IMPORTS DA IA DO GOOGLE (NOVA VERSÃO) ---
from google import genai
from google.genai import types

# Força o Python a procurar o .env na raiz correta do projeto
caminho_env = os.path.join(settings.BASE_DIR, '.env')
load_dotenv(caminho_env)

# Pega a chave
minha_chave = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=minha_chave) if minha_chave else None

# 🕵️‍♀️ PRINT DE INVESTIGAÇÃO (Vai aparecer no terminal)
print("\n--- STATUS DA IA ---")
if minha_chave:
    print(f"✅ Chave encontrada com sucesso! (Tamanho: {len(minha_chave)} caracteres)")
else:
    print("❌ ALERTA: A chave NÃO foi encontrada no arquivo .env!")
print("--------------------\n")



# ==========================================
# PÁGINAS PRINCIPAIS
# ==========================================
@login_required
def index(request):
    tipos_aco = TipoAco.objects.all().order_by('descricao')
    return render(request, 'estoque/index.html', {'tipos_aco': tipos_aco})

@login_required
def detalhe_tipo_aco(request, tipo_id):
    tipo = get_object_or_404(TipoAco, id=tipo_id)
    filtro_atual = request.GET.get('filtro', 'ativas')
    
    todas_bobinas = tipo.bobina_set.all().order_by('-mtc__data_recebimento')
    
    if filtro_atual == 'ativas':
        bobinas = [b for b in todas_bobinas if b.saldo_atual > 0]
    elif filtro_atual == 'finalizadas':
        bobinas = [b for b in todas_bobinas if b.saldo_atual <= 0]
    else:
        bobinas = todas_bobinas
        
    return render(request, 'estoque/detalhe_tipo_aco.html', {
        'tipo': tipo,
        'bobinas': bobinas,
        'filtro_atual': filtro_atual
    })

# ==========================================
# NÚCLEO: MTC E BOBINAS
# ==========================================
@login_required
def cadastrar_lote_mtc(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': 
        return redirect('index')

    if request.method == 'POST':
        mtc_form = MTCForm(request.POST, request.FILES)
        formset = BobinaFormSet(request.POST)

        if mtc_form.is_valid() and formset.is_valid():
            
            # 1. 🟢 PRÉ-VALIDAÇÃO: Verificar se alguma corrida (ou suas "irmãs") já existe no banco
            corridas_duplicadas = []
            
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    corrida_base = form.cleaned_data.get('corrida')
                    peso_total = int(form.cleaned_data.get('peso_inicial', 0))
                    
                    qtd = form.cleaned_data.get('qtd_irmas') or 1
                    if peso_total >= 5000: qtd = 2
                    if qtd > 2: qtd = 2

                    # Monta a lista de nomes exatos que o sistema tentará salvar (-1 e -2)
                    corridas_para_checar = []
                    if qtd == 2:
                        corridas_para_checar.extend([f"{corrida_base}-1", f"{corrida_base}-2"])
                    else:
                        corridas_para_checar.append(corrida_base)

                    # Vai ao banco ver se alguma delas já existe
                    for c in corridas_para_checar:
                        if Bobina.objects.filter(corrida=c).exists():
                            corridas_duplicadas.append(c)

            # 2. 🟢 O SEU AVISO: Se achar duplicada, avisa e NÃO SALVA NADA!
            if corridas_duplicadas:
                for c in corridas_duplicadas:
                    messages.error(request, f"O Lote de bobina {c} já foi cadastrado anteriormente.")
                
                # Devolve o utilizador para a tela com os dados que ele já digitou
                return render(request, 'estoque/mtc_bobina_form.html', {
                    'mtc_form': mtc_form, 
                    'formset': formset, 
                    'editando': False
                })

            # 3. 🟢 TUDO CERTO: Se passou pela nossa barreira, salva tudo!
            mtc = mtc_form.save()
            bobinas_salvas = 0
            
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    bobina_base = form.save(commit=False)
                    peso_total = int(bobina_base.peso_inicial)
                    
                    qtd = form.cleaned_data.get('qtd_irmas') or 1
                    if peso_total >= 5000: qtd = 2
                    if qtd > 2: qtd = 2

                    if qtd == 2:
                        peso_1 = math.ceil(peso_total / 2.0)
                        peso_2 = math.floor(peso_total / 2.0)
                        Bobina.objects.create(corrida=f"{bobina_base.corrida}-1", peso_inicial=peso_1, mtc=mtc, tipo_aco=bobina_base.tipo_aco, usuario_cadastro=request.user, resistencia=bobina_base.resistencia, escoamento=bobina_base.escoamento, alongamento=bobina_base.alongamento)
                        Bobina.objects.create(corrida=f"{bobina_base.corrida}-2", peso_inicial=peso_2, mtc=mtc, tipo_aco=bobina_base.tipo_aco, usuario_cadastro=request.user, resistencia=bobina_base.resistencia, escoamento=bobina_base.escoamento, alongamento=bobina_base.alongamento)
                        bobinas_salvas += 2
                    else:
                        bobina_base.usuario_cadastro = request.user
                        bobina_base.mtc = mtc
                        bobina_base.save()
                        bobinas_salvas += 1

            RegistroAuditoria.objects.create(tabela_afetada='MTC', identificador=mtc.num_controle, acao='CRIACAO', usuario=request.user, detalhes=f"Lote criado com {bobinas_salvas} bobinas.")
            
            # (Opcional) Avisar que deu tudo certo no final!
            messages.success(request, f"Lote gravado com sucesso com {bobinas_salvas} bobinas.")
            return redirect('index')
            
        else:
            # 4. 🟢 CAPTURA DE ERROS PADRÃO: Se o formulário for inválido por outro motivo
            
            # Erros do formulário principal (MTC)
            for error_list in mtc_form.errors.values():
                for erro in error_list:
                    # Intercepta a mensagem em inglês e traduz
                    if "already exists" in erro:
                        messages.error(request, "⚠️ Já existe um MTC cadastrado com esta mesma Identificação (NF / Container) e Data de Recebimento.")
                    else:
                        messages.error(request, erro)
            
            # Erros das bobinas
            for form in formset:
                # Oculta o erro padrão de duplicidade do Django para não mostrar a nossa mensagem e a dele juntas
                if 'corrida' in form.errors:
                    messages.error(request, "⚠️ Verifique o campo corrida: já existe uma bobina com este lote.")
                else:
                    for error_list in form.errors.values():
                        for erro in error_list:
                            messages.error(request, erro)

    else:
        mtc_form = MTCForm()
        formset = BobinaFormSet()

    return render(request, 'estoque/mtc_bobina_form.html', {'mtc_form': mtc_form, 'formset': formset, 'editando': False})

@login_required
def editar_lote_mtc(request, mtc_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': 
        return redirect('index')

    mtc = get_object_or_404(MTC, id=mtc_id)

    if request.method == 'POST':
        mtc_form = MTCForm(request.POST, request.FILES, instance=mtc)
        formset = BobinaFormSet(request.POST, instance=mtc)

        if mtc_form.is_valid() and formset.is_valid():
            mtc = mtc_form.save()
            
            bobinas_salvas = 0
            bobinas_excluidas = 0

            for form in formset.deleted_forms:
                if form.instance.pk:
                    if Consumo.objects.filter(bobina=form.instance).exists():
                        continue 
                    form.instance.delete()
                    bobinas_excluidas += 1

            for form in formset.forms:
                if form not in formset.deleted_forms and form.has_changed() or not form.instance.pk:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        bobina_base = form.save(commit=False)
                        peso_total = int(bobina_base.peso_inicial)
                        
                        if not bobina_base.pk:
                            qtd = form.cleaned_data.get('qtd_irmas') or 1
                            if peso_total >= 5000: qtd = 2
                            if qtd > 2: qtd = 2

                            if qtd == 2:
                                peso_1 = math.ceil(peso_total / 2.0)
                                peso_2 = math.floor(peso_total / 2.0)
                                Bobina.objects.create(corrida=f"{bobina_base.corrida}-1", peso_inicial=peso_1, mtc=mtc, tipo_aco=bobina_base.tipo_aco, usuario_cadastro=request.user, resistencia=bobina_base.resistencia, escoamento=bobina_base.escoamento, alongamento=bobina_base.alongamento)
                                Bobina.objects.create(corrida=f"{bobina_base.corrida}-2", peso_inicial=peso_2, mtc=mtc, tipo_aco=bobina_base.tipo_aco, usuario_cadastro=request.user, resistencia=bobina_base.resistencia, escoamento=bobina_base.escoamento, alongamento=bobina_base.alongamento)
                                bobinas_salvas += 2
                            else:
                                bobina_base.peso_inicial = peso_total
                                bobina_base.usuario_cadastro = request.user
                                bobina_base.mtc = mtc
                                bobina_base.save()
                                bobinas_salvas += 1
                        else:
                            bobina_base.peso_inicial = peso_total
                            bobina_base.save()
                            bobinas_salvas += 1

            RegistroAuditoria.objects.create(tabela_afetada='MTC / Bobinas', identificador=f"MTC: {mtc.num_controle}", acao='ALTERACAO', usuario=request.user, detalhes=f"Lote editado. Salvas/Atualizadas: {bobinas_salvas}. Excluídas: {bobinas_excluidas}.")
            return redirect('index')
    else:
        mtc_form = MTCForm(instance=mtc)
        formset = BobinaFormSet(instance=mtc)

    return render(request, 'estoque/mtc_bobina_form.html', {'mtc_form': mtc_form, 'formset': formset, 'editando': True})

@login_required
def excluir_lote_mtc(request, mtc_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': 
        return redirect('index')
        
    mtc = get_object_or_404(MTC, id=mtc_id)
    tem_consumo = Consumo.objects.filter(bobina__mtc=mtc).exists()
    
    if request.method == 'POST':
        if tem_consumo:
            return redirect('excluir_lote_mtc', mtc_id=mtc.id)
            
        RegistroAuditoria.objects.create(tabela_afetada='MTC', identificador=mtc.num_controle, acao='EXCLUSAO', usuario=request.user)
        mtc.delete()
        return redirect('index')
        
    return render(request, 'estoque/confirm_delete_mtc.html', {'mtc': mtc, 'tem_consumo': tem_consumo})

# ==========================================
# NÚCLEO: CONSUMO
# ==========================================
@login_required
def registrar_consumo(request):
    bobina_id = request.GET.get('bobina')
    bobina_selecionada = None
    if bobina_id:
        bobina_selecionada = get_object_or_404(Bobina, id=bobina_id)

    if request.method == 'POST':
        # ✅ Trava de segurança para o VISUALIZADOR não salvar
        if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR':
            return redirect('index')

        # Usando o nome correto do seu Form: ConsumoForm
        form = ConsumoForm(request.POST)
        if form.is_valid():
            consumo = form.save(commit=False)
            consumo.usuario = request.user
            consumo.bobina = bobina_selecionada
            consumo.save()
            return redirect(f"{reverse('registrar_consumo')}?bobina={bobina_selecionada.id}")
    else:
        # Usando o nome correto do seu Form: ConsumoForm
        form = ConsumoForm()

    # Usando o nome correto do seu Model: Consumo
    historico = Consumo.objects.filter(bobina=bobina_selecionada).order_by('-data_consumo') if bobina_selecionada else []

    return render(request, 'estoque/consumo_form.html', {
        'form': form,
        'bobina_selecionada': bobina_selecionada,
        'historico': historico,
    })
@login_required
def editar_consumo(request, consumo_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': 
        return redirect('index')
        
    consumo = get_object_or_404(Consumo, id=consumo_id)
    
    if request.method == 'POST':
        form = ConsumoForm(request.POST, instance=consumo)
        if form.is_valid():
            form.save()
            RegistroAuditoria.objects.create(tabela_afetada='Consumo', identificador=f"Consumo de {consumo.peso}kg - {consumo.bobina.corrida}", acao='ALTERACAO', usuario=request.user)
            return redirect('registrar_consumo')
    else:
        form = ConsumoForm(instance=consumo)
        
    return render(request, 'estoque/consumo_form.html', {'form': form, 'bobina_selecionada': consumo.bobina, 'editando': True})

@login_required
def excluir_consumo(request, consumo_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': 
        return redirect('index')
        
    consumo = get_object_or_404(Consumo, id=consumo_id)
    bobina_id = consumo.bobina.id
    
    if request.method == 'POST':
        RegistroAuditoria.objects.create(tabela_afetada='Consumo', identificador=f"Consumo de {consumo.peso}kg - {consumo.bobina.corrida}", acao='EXCLUSAO', usuario=request.user)
        consumo.delete()
        return redirect(f"/consumo/novo/?bobina={bobina_id}")
        
    return render(request, 'estoque/confirm_delete_padrao.html', {'item': f"Consumo de {consumo.peso}kg da corrida {consumo.bobina.corrida}", 'tipo': 'Consumo', 'url_cancelar': 'index'})

# ==========================================
# AUDITORIA
# ==========================================
@login_required
def relatorio_auditoria(request):
    if not hasattr(request.user, 'perfil') or request.user.perfil.tipo != 'ADM': 
        return redirect('index')
        
    # CORREÇÃO AQUI: Mudamos de '-data_acao' para '-data_hora'
    registros = RegistroAuditoria.objects.all().order_by('-data_hora')
    return render(request, 'estoque/auditoria.html', {'registros': registros})

# ==========================================
# CADASTROS AUXILIARES (COM TRAVAS DE SEGURANÇA)
# ==========================================
@login_required
def lista_fornecedores(request):
    fornecedores = Fornecedor.objects.all().order_by('nome')
    return render(request, 'estoque/fornecedor_list.html', {'fornecedores': fornecedores})

@login_required
def cadastrar_fornecedor(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_fornecedores')
    else: form = FornecedorForm()
    return render(request, 'estoque/fornecedor_form.html', {'form': form, 'editando': False})

@login_required
def editar_fornecedor(request, id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    fornecedor = get_object_or_404(Fornecedor, id=id)
    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor)
        if form.is_valid():
            form.save()
            return redirect('lista_fornecedores')
    else: form = FornecedorForm(instance=fornecedor)
    return render(request, 'estoque/fornecedor_form.html', {'form': form, 'editando': True})

@login_required
def excluir_fornecedor(request, id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    fornecedor = get_object_or_404(Fornecedor, id=id)
    
    # TRAVA: Tem MTC vinculado?
    tem_dependencia = fornecedor.mtc_set.exists()
    
    if request.method == 'POST':
        if tem_dependencia: return redirect('lista_fornecedores')
        fornecedor.delete()
        return redirect('lista_fornecedores')
        
    return render(request, 'estoque/confirm_delete_padrao.html', {
        'item': fornecedor, 
        'tipo': 'Fornecedor', 
        'url_cancelar': 'lista_fornecedores',
        'tem_dependencia': tem_dependencia,
        'mensagem_bloqueio': 'Este Fornecedor não pode ser excluído pois existem Lotes/MTCs vinculados a ele no sistema.'
    })

@login_required
def lista_tipos_aco(request):
    tipos = TipoAco.objects.all().order_by('descricao')
    return render(request, 'estoque/tipo_aco_list.html', {'tipos': tipos})

@login_required
def cadastrar_tipo_aco(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    if request.method == 'POST':
        form = TipoAcoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_tipos_aco')
    else: form = TipoAcoForm()
    return render(request, 'estoque/tipo_aco_form.html', {'form': form, 'editando': False})

@login_required
def editar_tipo_aco(request, id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    tipo = get_object_or_404(TipoAco, id=id)
    if request.method == 'POST':
        form = TipoAcoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            return redirect('lista_tipos_aco')
    else: form = TipoAcoForm(instance=tipo)
    return render(request, 'estoque/tipo_aco_form.html', {'form': form, 'editando': True})

@login_required
def excluir_tipo_aco(request, id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    tipo = get_object_or_404(TipoAco, id=id)
    
    # TRAVA: Tem bobina com esse aço?
    tem_dependencia = tipo.bobina_set.exists()
    
    if request.method == 'POST':
        if tem_dependencia: return redirect('lista_tipos_aco')
        tipo.delete()
        return redirect('lista_tipos_aco')
        
    return render(request, 'estoque/confirm_delete_padrao.html', {
        'item': tipo, 
        'tipo': 'Tipo de Aço', 
        'url_cancelar': 'lista_tipos_aco',
        'tem_dependencia': tem_dependencia,
        'mensagem_bloqueio': 'Este Tipo de Aço não pode ser excluído porque existem bobinas cadastradas utilizando-o. Delete as bobinas primeiro.'
    })

@login_required
def lista_tipos_consumo(request):
    tipos = TipoConsumo.objects.all().order_by('descricao')
    return render(request, 'estoque/tipo_consumo_list.html', {'tipos': tipos})

@login_required
def cadastrar_tipo_consumo(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    if request.method == 'POST':
        form = TipoConsumoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_tipos_consumo')
    else: form = TipoConsumoForm()
    return render(request, 'estoque/tipo_consumo_form.html', {'form': form, 'editando': False})

@login_required
def editar_tipo_consumo(request, id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    tipo = get_object_or_404(TipoConsumo, id=id)
    if request.method == 'POST':
        form = TipoConsumoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            return redirect('lista_tipos_consumo')
    else: form = TipoConsumoForm(instance=tipo)
    return render(request, 'estoque/tipo_consumo_form.html', {'form': form, 'editando': True})

@login_required
def excluir_tipo_consumo(request, id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': return redirect('index')
    tipo = get_object_or_404(TipoConsumo, id=id)
    
    # TRAVA: Tem apontamento com esse consumo?
    tem_dependencia = tipo.consumo_set.exists()
    
    if request.method == 'POST':
        if tem_dependencia: return redirect('lista_tipos_consumo')
        tipo.delete()
        return redirect('lista_tipos_consumo')
        
    return render(request, 'estoque/confirm_delete_padrao.html', {
        'item': tipo, 
        'tipo': 'Tipo de Consumo', 
        'url_cancelar': 'lista_tipos_consumo',
        'tem_dependencia': tem_dependencia,
        'mensagem_bloqueio': 'Este Tipo de Consumo não pode ser excluído pois existem históricos de apontamento de fábrica utilizando-o.'
    })

# ==========================================
# RELATÓRIOS
# ==========================================
@login_required
def relatorio_estoque_atual(request):
    # Pega o filtro da URL se o usuário pesquisou por um aço específico
    tipo_filtro = request.GET.get('tipo_aco')
    tipos = TipoAco.objects.all().order_by('descricao')

    if tipo_filtro:
        tipos = tipos.filter(id=tipo_filtro)

    dados_relatorio = []
    total_geral_saldo = 0
    total_geral_bobinas = 0

    for tipo in tipos:
        # A Mágica: Filtramos na memória do Python pois saldo_atual é uma @property
        bobinas_ativas = [b for b in tipo.bobina_set.all() if b.saldo_atual > 0]
        
        if bobinas_ativas:
            qtd_bobinas = len(bobinas_ativas)
            peso_total = sum(b.peso_inicial for b in bobinas_ativas)
            saldo_total = sum(b.saldo_atual for b in bobinas_ativas)
            
            total_geral_saldo += saldo_total
            total_geral_bobinas += qtd_bobinas

            dados_relatorio.append({
                'tipo': tipo,
                'qtd_bobinas': qtd_bobinas,
                'peso_total': peso_total,
                'saldo_total': saldo_total
            })

    # Busca todos os tipos apenas para preencher a caixa de seleção do Filtro
    todos_tipos = TipoAco.objects.all().order_by('descricao')

    return render(request, 'estoque/relatorio_estoque_atual.html', {
        'dados': dados_relatorio,
        'total_geral_saldo': total_geral_saldo,
        'total_geral_bobinas': total_geral_bobinas,
        'todos_tipos': todos_tipos,
        # Converte para int para o template saber qual opção deixar marcada no filtro
        'tipo_filtro': int(tipo_filtro) if tipo_filtro else '' 
    })

@login_required
def relatorio_todas_bobinas(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR': 
        return redirect('index')

    # Pega as listas de checkboxes marcados na URL
    tipos_selecionados = request.GET.getlist('tipo_aco')
    status_selecionados = request.GET.getlist('status')
    
    # Converte os IDs de string para inteiro para facilitar a marcação no HTML
    tipos_selecionados = [int(i) for i in tipos_selecionados if i.isdigit()]

    # 1. Busca no Banco de Dados
    bobinas_query = Bobina.objects.select_related('tipo_aco', 'mtc').all().order_by('-mtc__data_recebimento', 'corrida')
    
    # Filtra os aços marcados no Banco (se houver algum marcado)
    if tipos_selecionados:
        bobinas_query = bobinas_query.filter(tipo_aco__id__in=tipos_selecionados)

    # 2. Triagem de Status na memória do Python
    bobinas_filtradas = []
    total_peso = 0
    total_saldo = 0

    for bobina in bobinas_query:
        saldo = bobina.saldo_atual
        peso = bobina.peso_inicial
        
        # Define o status da bobina
        if saldo <= 0:
            status_atual = 'finalizada'
        elif saldo == peso:
            status_atual = 'fechada'
        else:
            status_atual = 'iniciada'

        # Se não marcou nenhum status (mostra tudo) OU se o status atual está entre os marcados
        if not status_selecionados or status_atual in status_selecionados:
            # Adiciona o status como um atributo dinâmico na bobina para usarmos no HTML
            bobina.status_visual = status_atual
            bobinas_filtradas.append(bobina)
            
            total_peso += peso
            total_saldo += saldo

    todos_tipos = TipoAco.objects.all().order_by('descricao')

    return render(request, 'estoque/relatorio_todas_bobinas.html', {
        'bobinas': bobinas_filtradas,
        'todos_tipos': todos_tipos,
        'tipos_selecionados': tipos_selecionados,
        'status_selecionados': status_selecionados,
        'total_peso': total_peso,
        'total_saldo': total_saldo,
        'tem_filtro': bool(tipos_selecionados or status_selecionados)
    })

@login_required
def imprimir_etiqueta(request, bobina_id):
    bobina = get_object_or_404(Bobina, id=bobina_id)

    # 1. CÁLCULO CORRIGIDO DA RELAÇÃO (% Esc/Res)
    relacao = 0
    if bobina.resistencia > 0:
        relacao = (bobina.escoamento / bobina.resistencia) * 100
    
    # 2. GERAÇÃO DO QR CODE (Com o número da Corrida)
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(bobina.corrida) # O conteúdo do QR é o número da corrida
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Transforma a imagem em texto (base64) para embutir no HTML
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return render(request, 'estoque/etiqueta_bobina.html', {
        'bobina': bobina,
        'relacao': relacao,
        'qr_code': qr_base64 # Passamos a imagem do QR Code pronta
    })

def processar_mtc_com_ia(arquivo_pdf, lista_fornecedores, lista_acos):
    if not client:
        print("Erro: Cliente IA não inicializado por falta de chave.")
        return None
        
    try:
        conteudo_arquivo = arquivo_pdf.read()
        
        # --- AQUI É O PROMPT ENVIADO PARA O IA ---
        prompt_dinamico = f"""
        Você é um extrator de dados de nível industrial.
        
        Abaixo estão os ÚNICOS cadastros válidos do nosso sistema:
        [FORNECEDORES PERMITIDOS]: {lista_fornecedores}
        [TIPOS DE AÇO PERMITIDOS]: {lista_acos}
        
        Analise o MTC anexado. O documento pode conter produtos de dimensões diferentes misturados na mesma tabela.
        
        Devolva um JSON puro seguindo OBRIGATORIAMENTE esta estrutura:
        {{
          "num_controle": "Nota fiscal, Lote ou PO Number",
          "fornecedor": "Copie o nome EXATO da lista de [FORNECEDORES PERMITIDOS]",
          "bobinas": [
            {{
              "_rascunho_liga": "Pense passo a passo: Qual é o GRADE/Aço principal do documento (ex: 410S)?",
              "_rascunho_dimensoes": "Pense passo a passo: Analisando ESTA linha exata, qual é a Espessura (menor valor) e o Comprimento (maior valor)?",
              "tipo_aco": "Com base nos seus rascunhos acima, copie o nome EXATO da lista de [TIPOS DE AÇO PERMITIDOS] que corresponde a esta chapa/bobina",
              "corrida": "Product NO ou Material ID exato desta linha",
              "peso_inicial": 0000,
              "escoamento": 000.0,
              "resistencia": 000.0,
              "alongamento": 00.0
            }}
          ],
          "auditoria_matematica": {{
            "peso_total_documento": 0000,
            "equacao_dos_pesos": "Escreva a soma matemática de todos os pesos extraídos para provar que não omitiu nenhum. Ex: 1473 + 1473 + 1454... = 26356",
            "soma_calculada": 0000,
            "status": "OK ou ERRO"
          }}
        }}
        
        REGRAS DE OURO:
        1. RASCUNHO OBRIGATÓRIO (CHAIN OF THOUGHT): 
           - Para cada item na tabela, preencha primeiro os campos '_rascunho_liga' e '_rascunho_dimensoes'. 
           - Lembre-se: Espessura = Menor valor numérico da dimensão. Comprimento = Maior valor numérico.
           - Apenas depois de "pensar" nestes dois campos, faça o cruzamento e preencha o 'tipo_aco' com a opção do nosso sistema.
           
        2. AUTOVERIFICAÇÃO MATEMÁTICA E EQUAÇÃO (ANTI-OMISSÃO):
           - Localize no fim da tabela do PDF o peso TOTAL e preencha em 'peso_total_documento'.
           - Escreva de forma literal a 'equacao_dos_pesos' mostrando a soma de CADA peso da lista 'bobinas'.
           - REGRA CRÍTICA: Se a 'soma_calculada' não for exatamente igual ao 'peso_total_documento', significa que você OMITIU linhas devido à preguiça. Se isso acontecer, refaça o processo internamente e adicione as corridas que faltam na lista até a equação matemática ficar 100% correta.
           
        3. O peso deve ser sempre um número inteiro em kg.
        """
        
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=[
                prompt_dinamico,
                types.Part.from_bytes(data=conteudo_arquivo, mime_type='application/pdf')
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        dados_extraidos = json.loads(response.text)
        return dados_extraidos
        # --- FIM DO PASSO 3 ---

    except Exception as e:
        print(f"Erro na leitura inteligente: {e}")
        return None

@login_required
def api_leitura_mtc(request):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        arquivo_pdf = request.FILES['arquivo']
        
        # 🟢 BUSCA O "GABARITO" NO BANCO DE DADOS (Traz apenas os nomes em formato de lista)
        lista_fornecedores = list(Fornecedor.objects.filter(ativo=True).values_list('nome', flat=True))
        lista_acos = list(TipoAco.objects.filter(ativo=True).values_list('descricao', flat=True)) # Ajuste 'descricao' para o nome do campo real do seu model
        
        # Passamos o gabarito para a função da IA
        dados = processar_mtc_com_ia(arquivo_pdf, lista_fornecedores, lista_acos)
        
        if dados:
            return JsonResponse({'sucesso': True, 'dados': dados})
        else:
            return JsonResponse({'sucesso': False, 'erro': 'A IA não conseguiu ler os dados.'})
            
    return JsonResponse({'sucesso': False, 'erro': 'Requisição inválida.'})

def api_pesquisar_bobina(request):
    termo = request.GET.get('q', '').strip()
    
    if not termo:
        return JsonResponse({'sucesso': True, 'resultados': []})
    
    # Faz a busca parcial ignorando maiúsculas/minúsculas (__icontains)
    # Trazemos apenas as 20 primeiras para não sobrecarregar o modal
    bobinas = Bobina.objects.filter(corrida__icontains=termo).select_related('tipo_aco')[:20]
    
    resultados = []
    for b in bobinas:
        # Pega a URL correta da tela de detalhes baseada no tipo de aço
        link_tela_detalhes = reverse('detalhe_tipo', args=[b.tipo_aco.id]) if b.tipo_aco else '/'
        
        resultados.append({
            'id': b.id,
            'corrida': b.corrida,
            'tipo_aco': b.tipo_aco.descricao if b.tipo_aco else 'N/A',
            'data': b.mtc.data_recebimento.strftime('%d/%m/%Y') if hasattr(b, 'mtc') and b.mtc else '-',
            'peso': float(b.peso_inicial),
            'saldo': float(getattr(b, 'saldo_atual', b.peso_inicial)), 
            'url_redirecionamento': link_tela_detalhes # 🟢 Nova variável enviada para o JavaScript
        })
        
    return JsonResponse({'sucesso': True, 'resultados': resultados})

def api_reportar_erro_ia(request):
    if request.method == 'POST':
        try:
            # Lemos os dados que o JavaScript mandou via fetch
            dados = json.loads(request.body)
            numero_mtc = dados.get('numero_mtc', 'N/A')
            detalhes_erro = dados.get('detalhes_erro', 'N/A')
            
            # Guardamos o erro na nossa nova tabela do banco de dados
            RelatorioDivergenciaIA.objects.create(
                usuario=request.user if request.user.is_authenticated else None,
                numero_mtc=numero_mtc,
                detalhes_erro=detalhes_erro,
                status='PENDENTE'
            )
            
            return JsonResponse({'sucesso': True})
            
        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})
            
    return JsonResponse({'sucesso': False, 'erro': 'Método inválido'})
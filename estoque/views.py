from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import math
import qrcode
from io import BytesIO
import base64
from django.db.models import F


from .models import TipoAco, Bobina, Fornecedor, Consumo, RegistroAuditoria, MTC, TipoConsumo
from .forms import FornecedorForm, BobinaFormSet, ConsumoForm, MTCForm, TipoAcoForm, TipoConsumoForm

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
            return redirect('index')
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
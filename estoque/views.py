import math
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from .forms import FornecedorForm, BobinaFormSet, ConsumoForm, MTCForm
from .models import TipoAco, Bobina, Fornecedor, Consumo, RegistroAuditoria, MTC

@login_required
def index(request):
    tipos_aco = TipoAco.objects.all()
    return render(request, 'estoque/index.html', {'tipos_aco': tipos_aco})

@login_required
def detalhe_tipo_aco(request, tipo_id):
    tipo = get_object_or_404(TipoAco, id=tipo_id) 
    
    # NOVO: Captura qual filtro o usuário clicou (padrão é 'ativas')
    filtro = request.GET.get('filtro', 'ativas')
    
    # Pega todas as bobinas deste tipo, ordenadas pelas mais novas
    bobinas_raw = Bobina.objects.filter(tipo_aco=tipo).order_by('-data_cadastro')
    bobinas = []
    
    # Filtra em tempo real baseado no status dinâmico
    for b in bobinas_raw:
        status = b.status_dinamico
        if filtro == 'ativas' and status != 'Finalizada':
            bobinas.append(b)
        elif filtro == 'finalizadas' and status == 'Finalizada':
            bobinas.append(b)
        elif filtro == 'todas':
            bobinas.append(b)

    return render(request, 'estoque/detalhe_tipo_aco.html', {
        'tipo': tipo, 
        'bobinas': bobinas,
        'filtro_atual': filtro # Passamos o filtro atual para o HTML saber qual botão pintar de azul
    })

@login_required
def lista_fornecedores(request):
    fornecedores = Fornecedor.objects.all().order_by('nome')
    return render(request, 'estoque/fornecedor_list.html', {'fornecedores': fornecedores})

@login_required
def cadastrar_fornecedor(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR':
        return redirect('index')

    if request.method == 'POST':
        form = FornecedorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = FornecedorForm()
    return render(request, 'estoque/fornecedor_form.html', {'form': form})

@login_required
def cadastrar_lote_mtc(request):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR':
        return redirect('index')

    if request.method == 'POST':
        mtc_form = MTCForm(request.POST, request.FILES)
        
        if mtc_form.is_valid():
            mtc = mtc_form.save(commit=False)
            mtc.usuario_cadastro = request.user
            mtc.save()
            
            formset = BobinaFormSet(request.POST, instance=mtc)
            
            if formset.is_valid():
                bobinas_salvas = 0
                for form in formset:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        bobina_base = form.save(commit=False)
                        
                        peso_total = int(bobina_base.peso_inicial)
                        qtd = form.cleaned_data.get('qtd_irmas', 1)
                        
                        if peso_total >= 5000:
                            qtd = 2

                        if qtd > 2:
                            qtd = 2

                        if qtd == 2:
                            peso_1 = math.ceil(peso_total / 2.0)
                            peso_2 = math.floor(peso_total / 2.0)

                            Bobina.objects.create(
                                corrida=f"{bobina_base.corrida}-1",
                                peso_inicial=peso_1,
                                mtc=mtc,
                                tipo_aco=bobina_base.tipo_aco,
                                usuario_cadastro=request.user,
                                resistencia=bobina_base.resistencia,
                                escoamento=bobina_base.escoamento,
                                alongamento=bobina_base.alongamento
                            )
                            Bobina.objects.create(
                                corrida=f"{bobina_base.corrida}-2",
                                peso_inicial=peso_2,
                                mtc=mtc,
                                tipo_aco=bobina_base.tipo_aco,
                                usuario_cadastro=request.user,
                                resistencia=bobina_base.resistencia,
                                escoamento=bobina_base.escoamento,
                                alongamento=bobina_base.alongamento
                            )
                            bobinas_salvas += 2
                        else:
                            bobina_base.peso_inicial = peso_total
                            bobina_base.usuario_cadastro = request.user
                            bobina_base.mtc = mtc
                            bobina_base.save()
                            bobinas_salvas += 1

                RegistroAuditoria.objects.create(
                    tabela_afetada='MTC',
                    identificador=f"MTC: {mtc.num_controle}",
                    acao='CRIACAO',
                    usuario=request.user,
                    detalhes=f"Cadastrado junto com {bobinas_salvas} bobinas."
                )
                
                # NOVO: Redireciona para o Dashboard em vez da lista geral que foi excluída
                return redirect('index') 
            else:
                mtc.delete() 
        else:
            formset = BobinaFormSet(request.POST)
    else:
        mtc_form = MTCForm()
        formset = BobinaFormSet()

    return render(request, 'estoque/mtc_bobina_form.html', {
        'mtc_form': mtc_form,
        'formset': formset
    })

@login_required
def registrar_consumo(request):
    bobina_id = request.GET.get('bobina')
    historico = None
    bobina_selecionada = None
    
    if bobina_id:
        bobina_selecionada = get_object_or_404(Bobina, id=bobina_id)
        historico = Consumo.objects.filter(bobina=bobina_selecionada).order_by('-data_consumo')

    if request.method == 'POST':
        if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR':
            return redirect('index')

        form = ConsumoForm(request.POST)
        if form.is_valid():
            try:
                consumo = form.save(commit=False)
                consumo.usuario = request.user
                consumo.peso = int(consumo.peso)
                consumo.save() 
                return redirect(f"{request.path}?bobina={consumo.bobina.id}")
            except ValidationError as e:
                form.add_error(None, e) 
    else:
        form = ConsumoForm(initial={'bobina': bobina_id} if bobina_id else None)
        
    return render(request, 'estoque/consumo_form.html', {
        'form': form, 'historico': historico, 'bobina_selecionada': bobina_selecionada, 'editando': False
    })

@login_required
def editar_consumo(request, consumo_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR':
        return redirect('index')

    consumo = get_object_or_404(Consumo, id=consumo_id)
    bobina_selecionada = consumo.bobina
    
    if request.method == 'POST':
        form = ConsumoForm(request.POST, instance=consumo)
        if form.is_valid():
            try:
                consumo_editado = form.save(commit=False)
                consumo_editado.peso = int(consumo_editado.peso)
                consumo_editado.save()
                return redirect(f"/consumo/novo/?bobina={bobina_selecionada.id}")
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = ConsumoForm(instance=consumo)
        
    return render(request, 'estoque/consumo_form.html', {
        'form': form, 'bobina_selecionada': bobina_selecionada, 'editando': True
    })

@login_required
def excluir_consumo(request, consumo_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR':
        return redirect('index')

    consumo = get_object_or_404(Consumo, id=consumo_id)
    bobina_id = consumo.bobina.id
    if request.method == 'POST':
        consumo.delete()
        return redirect(f"/consumo/novo/?bobina={bobina_id}")
    return render(request, 'estoque/consumo_confirm_delete.html', {'consumo': consumo})

@login_required
def relatorio_auditoria(request):
    # NOVO: Trava de segurança rigorosa. Se não for ADM, manda de volta pro início.
    if not hasattr(request.user, 'perfil') or request.user.perfil.tipo != 'ADM':
        return redirect('index')
        
    registros = RegistroAuditoria.objects.all().order_by('-data_hora')
    return render(request, 'estoque/auditoria_list.html', {'registros': registros})

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
                    form.instance.delete()
                    bobinas_excluidas += 1

            for form in formset.forms:
                if form not in formset.deleted_forms and form.has_changed() or not form.instance.pk:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        bobina_base = form.save(commit=False)
                        peso_total = int(bobina_base.peso_inicial)
                        
                        if not bobina_base.pk:
                            # CORREÇÃO: Pega o valor ou assume 1 se estiver vazio
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

            RegistroAuditoria.objects.create(
                tabela_afetada='MTC / Bobinas',
                identificador=f"MTC: {mtc.num_controle}",
                acao='ALTERACAO',
                usuario=request.user,
                detalhes=f"Lote editado. Salvas/Atualizadas: {bobinas_salvas}. Excluídas: {bobinas_excluidas}."
            )
            return redirect('index')
        else:
            formset = BobinaFormSet(request.POST)
    else:
        mtc_form = MTCForm(instance=mtc)
        formset = BobinaFormSet(instance=mtc)

    return render(request, 'estoque/mtc_bobina_form.html', {
        'mtc_form': mtc_form,
        'formset': formset,
        'editando': True 
    })

@login_required
def excluir_lote_mtc(request, mtc_id):
    if hasattr(request.user, 'perfil') and request.user.perfil.tipo == 'VISUALIZADOR':
        return redirect('index')

    mtc = get_object_or_404(MTC, id=mtc_id)
    
    if request.method == 'POST':
        RegistroAuditoria.objects.create(
            tabela_afetada='MTC',
            identificador=f"MTC: {mtc.num_controle}",
            acao='EXCLUSAO',
            usuario=request.user,
            detalhes="MTC e todas as suas bobinas atreladas foram excluídos."
        )
        mtc.delete()
        return redirect('index')
        
    return render(request, 'estoque/mtc_confirm_delete.html', {'mtc': mtc})
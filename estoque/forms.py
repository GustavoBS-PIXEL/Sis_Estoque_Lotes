from django import forms
from django.forms import inlineformset_factory
from .models import Fornecedor, Bobina, Consumo, MTC

class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ['nome', 'nacional', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da Empresa'}),
            'nacional': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class MTCForm(forms.ModelForm):
    class Meta:
        model = MTC
        fields = ['num_controle', 'data_recebimento', 'fornecedor', 'arquivo']
        widgets = {
            'num_controle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: NF 12345 ou GZ-08'}),
            
            # A CORREÇÃO MÁGICA ESTÁ AQUI ABAIXO (format='%Y-%m-%d')
            'data_recebimento': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,image/*'}),
        }

class BobinaForm(forms.ModelForm):
    qtd_irmas = forms.IntegerField(
        initial=1, 
        min_value=1, 
        max_value=2,
        required=False, # <--- A CORREÇÃO MÁGICA AQUI
        label='Dividir em (Qtd)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'style': 'max-width: 100px;'})
    )

    class Meta:
        model = Bobina
        fields = ['corrida', 'tipo_aco', 'peso_inicial', 'resistencia', 'escoamento', 'alongamento']
        widgets = {
            'corrida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nº da Corrida Mãe'}),
            'peso_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'placeholder': 'Peso Inteiro (kg)'}),
            'tipo_aco': forms.Select(attrs={'class': 'form-select'}),
            'resistencia': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'escoamento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'alongamento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

BobinaFormSet = inlineformset_factory(
    MTC, Bobina, form=BobinaForm,
    extra=1, 
    can_delete=True 
)

class ConsumoForm(forms.ModelForm):
    class Meta:
        model = Consumo
        fields = ['bobina', 'tipo_consumo', 'peso', 'observacao']
        widgets = {
            'bobina': forms.Select(attrs={'class': 'form-select'}),
            'tipo_consumo': forms.Select(attrs={'class': 'form-select'}),
            'peso': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
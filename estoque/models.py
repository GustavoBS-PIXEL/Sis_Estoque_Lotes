from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum, Avg
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Fornecedor(models.Model):
    nome = models.CharField(max_length=45, unique=True)
    nacional = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name_plural = "Fornecedores"

class TipoAco(models.Model):
    descricao = models.CharField(max_length=45)
    largura = models.DecimalField(max_digits=10, decimal_places=2)
    espessura = models.DecimalField(max_digits=10, decimal_places=2)
    liga_metalica = models.CharField(max_length=45)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name = "Tipo de Aço"
        verbose_name_plural = "Tipos de Aço"

    @property
    def total_estoque(self):
        return sum(bobina.saldo_atual for bobina in self.bobina_set.all())

    @property
    def media_entrega(self):
        seis_meses_atras = timezone.now() - timedelta(days=180)
        total_recebido = self.bobina_set.filter(
            data_cadastro__gte=seis_meses_atras
        ).aggregate(Sum('peso_inicial'))['peso_inicial__sum'] or 0
        return total_recebido / 6

    @property
    def media_consumo(self):
        seis_meses_atras = timezone.now() - timedelta(days=180)
        total_consumido = Consumo.objects.filter(
            bobina__tipo_aco=self, 
            data_consumo__gte=seis_meses_atras
        ).aggregate(Sum('peso'))['peso__sum'] or 0
        return total_consumido / 6

class MTC(models.Model):
    # Alterado o nome de exibição para acomodar letras e números
    num_controle = models.CharField(max_length=45, verbose_name="Identificação (NF / Container)")
    data_recebimento = models.DateField(verbose_name="Data de Recebimento")
    arquivo = models.FileField(upload_to='mtcs/', null=True, blank=True)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, related_name='mtcs')
    usuario_cadastro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Lote {self.num_controle} - {self.fornecedor.nome}"

    class Meta:
        # NOVO: Trava no banco de dados. Impede a mesma identificação no mesmo dia.
        constraints = [
            models.UniqueConstraint(fields=['num_controle', 'data_recebimento'], name='unique_mtc_por_dia')
        ]

class Bobina(models.Model):
    corrida = models.CharField(max_length=45, unique=True)
    peso_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    mtc = models.ForeignKey(MTC, on_delete=models.CASCADE)
    tipo_aco = models.ForeignKey(TipoAco, on_delete=models.CASCADE)
    usuario_cadastro = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    resistencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Resistência")
    escoamento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Escoamento")
    alongamento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Alongamento (%)")

    def __str__(self):
        return f"Bobina {self.corrida}"

    @property
    def saldo_atual(self):
        total_consumido = self.consumo_set.aggregate(Sum('peso'))['peso__sum'] or 0
        return self.peso_inicial - total_consumido

    @property
    def status_dinamico(self):
        if not self.consumo_set.exists():
            return "Fechada"
        return "Aberta" if self.saldo_atual > 0 else "Finalizada"

    @property
    def esc_res_percentual(self):
        if self.resistencia and self.escoamento and self.resistencia > 0:
            return (self.escoamento / self.resistencia) * 100
        return 0

class TipoConsumo(models.Model):
    descricao = models.CharField(max_length=45)
    def __str__(self): return self.descricao

class Consumo(models.Model):
    bobina = models.ForeignKey(Bobina, on_delete=models.CASCADE)
    tipo_consumo = models.ForeignKey(TipoConsumo, on_delete=models.CASCADE)
    peso = models.DecimalField(max_digits=10, decimal_places=2)
    data_consumo = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True, null=True, verbose_name="Observações / OP")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def clean(self):
        outros_consumos = self.bobina.consumo_set.exclude(pk=self.pk) if self.pk else self.bobina.consumo_set.all()
        total_outros = outros_consumos.aggregate(Sum('peso'))['peso__sum'] or 0
        saldo_disponivel = self.bobina.peso_inicial - total_outros

        if self.peso > saldo_disponivel:
            raise ValidationError(f"Saldo insuficiente! Disponível para esta baixa: {saldo_disponivel}kg")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Perfil(models.Model):
    TIPOS = (
        ('ADM', 'Administrador'),
        ('PADRAO', 'Usuário Padrão'),
        ('VISUALIZADOR', 'Visualizador'),
    )
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='VISUALIZADOR')

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo}"

@receiver(post_save, sender=User)
def gerenciar_perfil_usuario(sender, instance, **kwargs):
    if not hasattr(instance, 'perfil'):
        tipo_inicial = 'ADM' if instance.is_superuser else 'VISUALIZADOR'
        Perfil.objects.create(usuario=instance, tipo=tipo_inicial)
    else:
        instance.perfil.save()

class RegistroAuditoria(models.Model):
    ACOES = (('CRIACAO', 'Criação'), ('ALTERACAO', 'Alteração'), ('EXCLUSAO', 'Exclusão'))
    tabela_afetada = models.CharField(max_length=50)
    identificador = models.CharField(max_length=100)
    acao = models.CharField(max_length=20, choices=ACOES)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    detalhes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.data_hora|date:'d/m/Y H:i'} - {self.usuario} - {self.acao} {self.tabela_afetada}"
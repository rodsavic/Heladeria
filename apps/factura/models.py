from django.db import models
from django.db.models import Q

from apps.clientes.models import Cliente
from apps.ventas.models import Venta


class Timbrado(models.Model):
    id_timbrado = models.BigAutoField(primary_key=True)
    nro_timbrado = models.BigIntegerField(db_column='nro_timbrado', null=False, blank=False)
    ruc = models.CharField(db_column='ruc', max_length=11, null=False, blank=False)
    fecha_inicio = models.DateTimeField(db_column='fecha_inicio', null=False, blank=False)
    fecha_fin = models.DateTimeField(db_column='fecha_fin', null=False, blank=False)
    nro_factura_desde = models.CharField(db_column='nro_factura_desde',max_length=15, null=False, blank=False)
    nro_factura_hasta = models.CharField(db_column='nro_factura_hasta', max_length=15, null=False, blank=False)
    usuario_creacion = models.BigIntegerField(db_column='usuario_creacion', null=False)

    class Meta:
        db_table = 'timbrado'
        verbose_name = 'Timbrado'
        verbose_name_plural = 'Timbrados'

    def __str__(self):
        return f"Timbrado {self.nro_timbrado} - {self.fecha_inicio} - - {self.fecha_inicio}"


class FacturaQuerySet(models.QuerySet):
    def de_venta(self, venta):
        """Facturas que incluyen la venta, como venta principal o agrupada."""
        return self.filter(Q(id_venta=venta) | Q(ventas=venta)).distinct()


def facturas_de_ventas(ids_ventas, estados):
    """Devuelve {id_venta: Factura} con la factura (en alguno de `estados`)
    de cada venta, sea su venta principal o una venta agrupada."""
    resultado = {}
    for factura in Factura.objects.filter(id_venta__in=ids_ventas, estado__in=estados):
        resultado[factura.id_venta_id] = factura
    agrupadas = Factura.ventas.through.objects.filter(
        venta_id__in=ids_ventas, factura__estado__in=estados
    ).select_related('factura')
    for relacion in agrupadas:
        resultado.setdefault(relacion.venta_id, relacion.factura)
    return resultado


class Factura(models.Model):
    ESTADO_EMITIDA = 'EMITIDA'
    ESTADO_ANULADA = 'ANULADA'
    ESTADOS = (
        (ESTADO_EMITIDA, 'Emitida'),
        (ESTADO_ANULADA, 'Anulada'),
    )

    TIPO_CONTADO = 'CONTADO'
    TIPO_CREDITO = 'CREDITO'
    TIPOS = (
        (TIPO_CONTADO, 'Al contado'),
        (TIPO_CREDITO, 'Crédito'),
    )

    TRANSACCION_MERCADERIA = 1
    TRANSACCION_SERVICIOS = 2

    id_factura = models.AutoField(primary_key=True)
    nro_factura = models.CharField(db_column='nro_factura', max_length=25, null=False, blank=False, unique=True)
    # Venta principal. Si la factura agrupa varias ventas es la primera de
    # `ventas`; las facturas de una sola venta dejan `ventas` vacio.
    id_venta = models.ForeignKey(Venta, models.DO_NOTHING, db_column='id_venta')
    ventas = models.ManyToManyField(Venta, related_name='facturas_agrupadas', blank=True, db_table='factura_venta')
    # Receptor elegido al facturar; si es nulo se usa el cliente de la venta.
    id_cliente = models.ForeignKey(Cliente, models.DO_NOTHING, db_column='id_cliente', null=True, blank=True)
    id_tipo = models.IntegerField(db_column='id_tipo', null=False, blank=False, default=1)
    tipo_factura = models.CharField(max_length=10, choices=TIPOS, default=TIPO_CONTADO)
    forma_pago = models.CharField(max_length=120, blank=True, default='')
    estado = models.CharField(max_length=10, choices=ESTADOS, default=ESTADO_EMITIDA)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    nombre_empresa = models.CharField(max_length=150, blank=True, default='')
    ruc_empresa = models.CharField(max_length=20, blank=True, default='')
    direccion_empresa = models.CharField(max_length=255, blank=True, default='')
    nro_timbrado = models.CharField(max_length=30, blank=True, default='')
    vigencia_timbrado_desde = models.DateField(null=True, blank=True)
    # Codigo SIFEN de tipoTransaccion (1=venta de mercaderia, 2=prestacion de servicios).
    tipo_transaccion = models.PositiveSmallIntegerField(default=TRANSACCION_MERCADERIA)

    # Integracion FacturaSend / SIFEN
    ESTADO_SIFEN_BORRADOR = -1
    ESTADO_SIFEN_GENERADO = 0
    ESTADO_SIFEN_ENVIADO_LOTE = 1
    ESTADO_SIFEN_APROBADO = 2
    ESTADO_SIFEN_APROBADO_OBS = 3
    ESTADO_SIFEN_RECHAZADO = 4
    ESTADO_SIFEN_INEXISTENTE = 98
    ESTADO_SIFEN_CANCELADO = 99
    ESTADOS_SIFEN = (
        (ESTADO_SIFEN_BORRADOR, 'Borrador'),
        (ESTADO_SIFEN_GENERADO, 'Generado DE'),
        (ESTADO_SIFEN_ENVIADO_LOTE, 'Enviado en lote'),
        (ESTADO_SIFEN_APROBADO, 'Aprobado'),
        (ESTADO_SIFEN_APROBADO_OBS, 'Aprobado con observación'),
        (ESTADO_SIFEN_RECHAZADO, 'Rechazado'),
        (ESTADO_SIFEN_INEXISTENTE, 'Inexistente'),
        (ESTADO_SIFEN_CANCELADO, 'Cancelado'),
    )

    cdc = models.CharField(max_length=44, blank=True, default='', db_index=True)
    estado_sifen = models.IntegerField(choices=ESTADOS_SIFEN, default=ESTADO_SIFEN_BORRADOR)
    respuesta_sifen = models.TextField(blank=True, default='')

    # Envio del KuDE por correo (lo hace FacturaSend al aprobarse el DE)
    email_verificado = models.BooleanField(default=False)
    email_reintentos = models.PositiveSmallIntegerField(default=0)
    # Ultimo envio de respaldo por Gmail (cuando falla el correo de FacturaSend)
    fecha_email_respaldo = models.DateTimeField(null=True, blank=True)

    objects = FacturaQuerySet.as_manager()

    class Meta:
        db_table = 'factura'
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'

    def __str__(self):
        return f"Factura {self.nro_factura}"

    @property
    def cliente(self):
        return self.id_cliente if self.id_cliente_id else self.id_venta.id_cliente

    def get_ventas(self):
        """Ventas que cubre la factura, de la mas antigua a la mas reciente."""
        if not hasattr(self, '_ventas_cache'):
            agrupadas = list(self.ventas.order_by('fecha_venta', 'id_venta')) if self.pk else []
            self._ventas_cache = agrupadas or [self.id_venta]
        return self._ventas_cache

    @property
    def es_agrupada(self):
        return len(self.get_ventas()) > 1

    @property
    def total(self):
        return sum(venta.total_venta for venta in self.get_ventas())

    @property
    def total_iva_10(self):
        return sum(venta.total_iva_10 for venta in self.get_ventas())

    @property
    def total_iva_5(self):
        return sum(venta.total_iva_5 for venta in self.get_ventas())

    @property
    def observacion(self):
        return '\n'.join(venta.observacion for venta in self.get_ventas() if venta.observacion)


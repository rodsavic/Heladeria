from django.db import models

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

    id_factura = models.AutoField(primary_key=True)
    nro_factura = models.CharField(db_column='nro_factura', max_length=25, null=False, blank=False, unique=True)
    id_venta = models.ForeignKey(Venta, models.DO_NOTHING, db_column='id_venta')
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
    vigencia_timbrado_hasta = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'factura'
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'

    def __str__(self):
        return f"Factura {self.nro_factura}"


from django.db import models

from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.tipo_pago.models import TipoPago

class Venta(models.Model):
    id_venta = models.BigAutoField(primary_key=True)
    fecha_venta = models.DateTimeField(db_column='fecha_venta', auto_now_add=True)
    total_iva_10 = models.FloatField(db_column='total_iva_10', null=False)
    total_iva_5 = models.FloatField(db_column='total_iva_5', null=False)
    total_venta = models.FloatField(db_column='total_venta', null=False)
    usuario_creacion = models.BigIntegerField(db_column='usuario_creacion', null=False)
    id_cliente = models.ForeignKey(Cliente, models.DO_NOTHING, db_column='id_cliente', null=False)
    id_tipo_pago = models.ForeignKey(TipoPago, models.DO_NOTHING, db_column='id_tipo_pago', null=False)

    class Meta:
        managed = False
        db_table = 'ventas'
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'

    def __str__(self):
        return f"Venta {self.id_venta} - {self.fecha_venta}"
    

class VentaDetalle(models.Model):
    id_detalle = models.BigAutoField(primary_key=True)
    total_detalle = models.FloatField(db_column='total_detalle', null=False)
    cantidad_producto = models.FloatField(db_column='cantidad_producto', null=False)
    id_venta = models.ForeignKey(Venta, models.DO_NOTHING, db_column='id_venta')
    id_producto = models.ForeignKey(Producto, models.DO_NOTHING, db_column='id_producto')

    class Meta:
        managed = False
        db_table = 'venta_detalle'
        verbose_name = 'Venta Detalle'
        verbose_name_plural = 'Ventas Detalles'

    def __str__(self):
        return f"Detalle {self.id_detalle} - Venta {self.id_venta} - Producto {self.id_producto}"


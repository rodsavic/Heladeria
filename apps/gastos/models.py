from django.db import models

from apps.tipo_pago.models import TipoPago


class Gasto(models.Model):
    id_gasto = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=255, db_column="descripcion", null=False)
    costo = models.DecimalField(max_digits=12, decimal_places=2, db_column="costo", null=False)
    fecha = models.DateField(db_column="fecha", null=False)
    id_tipo_pago = models.ForeignKey(TipoPago, models.DO_NOTHING, db_column="id_tipo_pago", null=True, blank=True)
    usuario_creacion = models.IntegerField(db_column="usuario_creacion", null=True, blank=True)
    usuario_modificacion = models.IntegerField(db_column="usuario_modificacion", null=True, blank=True)
    fecha_creacion = models.DateTimeField(db_column="fecha_creacion", auto_now_add=True)
    fecha_modificacion = models.DateTimeField(db_column="fecha_modificacion", null=True, blank=True)

    class Meta:
        db_table = "gastos"
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"

    def __str__(self):
        return f"{self.descripcion} - {self.costo}"


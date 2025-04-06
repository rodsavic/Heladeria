from django.db import models

# Create your models here.
class TipoPago(models.Model):
    id_tipo_pago = models.BigAutoField(primary_key=True)
    descripcion = models.CharField(max_length=50, null=False, db_column='descripcion')

    class Meta:
        managed = False
        db_table = 'tipo_pago'
        verbose_name = 'Tipo Pago'
        verbose_name_plural = 'Tipos de Pago'

    def __str__(self):
        return f"Tipo de pago {self.id_tipo_pago} - {self.descripcion}"
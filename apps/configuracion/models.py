from django.db import models


class ConfiguracionEmpresa(models.Model):
    nombre_empresa = models.CharField(max_length=150)
    ruc = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255)
    nro_timbrado = models.CharField(max_length=30)
    vigencia_timbrado_desde = models.DateField()
    vigencia_timbrado_hasta = models.DateField()
    establecimiento = models.CharField(max_length=3, default='001')
    punto_expedicion = models.CharField(max_length=3, default='001')
    secuencia_actual = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'configuracion_empresa'
        verbose_name = 'Configuracion de Empresa'
        verbose_name_plural = 'Configuracion de Empresa'

    def __str__(self):
        return self.nombre_empresa

    def generar_nro_factura(self):
        return f"{self.establecimiento}-{self.punto_expedicion}-{self.secuencia_actual:07d}"

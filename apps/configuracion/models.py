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
    facturasend_url = models.CharField(max_length=255, blank=True, default='', help_text='Ej: https://api.facturasend.com.py/tenantId')
    facturasend_api_key = models.CharField(max_length=255, blank=True, default='')
    facturasend_sincrono = models.BooleanField(default=False)
    # Producto generico (ej. "Servicio de alquiler") que se usa como base de las
    # lineas de los contratos de alquiler: aporta codigo y unidad de medida SET.
    producto_alquiler = models.ForeignKey(
        'productos.Producto', models.SET_NULL, null=True, blank=True, related_name='+'
    )

    class Meta:
        db_table = 'configuracion_empresa'
        verbose_name = 'Configuracion de Empresa'
        verbose_name_plural = 'Configuracion de Empresa'

    def __str__(self):
        return self.nombre_empresa

    def generar_nro_factura(self):
        return f"{self.establecimiento}-{self.punto_expedicion}-{self.secuencia_actual:07d}"

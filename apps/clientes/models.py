from django.db import models

from apps.catalogos.models import Ciudad, Pais

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    documento = models.CharField(max_length=16, db_column= 'documento',null=False)
    nombre = models.CharField(max_length=100, db_column= 'nombre',null=False)
    apellido = models.CharField(max_length=100, db_column= 'apellido',null=False)
    correo = models.CharField(max_length=100, db_column= 'correo',null=False)
    celular = models.CharField(max_length=50, db_column= 'celular',null=False)
    direccion = models.CharField(max_length=255,db_column= 'direccion', null=True)
    estado = models.CharField(max_length=16, db_column= 'estado', null=True)

    # Campos requeridos por SIFEN / FacturaSend
    TIPO_DOC_CEDULA_PARAGUAYA = 1
    TIPO_DOC_PASAPORTE = 2
    TIPO_DOC_CEDULA_EXTRANJERA = 3
    TIPO_DOC_CARNET_RESIDENCIA = 4
    TIPO_DOC_INNOMINADO = 5
    TIPO_DOC_TARJETA_DIPLOMATICA = 6
    TIPO_DOC_OTRO = 9
    TIPOS_DOCUMENTO = (
        (TIPO_DOC_CEDULA_PARAGUAYA, 'Cédula paraguaya'),
        (TIPO_DOC_PASAPORTE, 'Pasaporte'),
        (TIPO_DOC_CEDULA_EXTRANJERA, 'Cédula extranjera'),
        (TIPO_DOC_CARNET_RESIDENCIA, 'Carnet de residencia'),
        (TIPO_DOC_INNOMINADO, 'Innominado'),
        (TIPO_DOC_TARJETA_DIPLOMATICA, 'Tarjeta diplomática'),
        (TIPO_DOC_OTRO, 'Otro'),
    )
    TIPOS_DOCUMENTO_EXTRANJERO = (
        TIPO_DOC_PASAPORTE,
        TIPO_DOC_CEDULA_EXTRANJERA,
        TIPO_DOC_CARNET_RESIDENCIA,
        TIPO_DOC_TARJETA_DIPLOMATICA,
    )

    OPERACION_B2B = 'B2B'
    OPERACION_B2C = 'B2C'
    OPERACION_B2G = 'B2G'
    OPERACION_B2F = 'B2F'
    TIPOS_OPERACION = (
        (OPERACION_B2B, 'B2B - Empresa'),
        (OPERACION_B2C, 'B2C - Consumidor final'),
        (OPERACION_B2G, 'B2G - Gobierno'),
        (OPERACION_B2F, 'B2F - Extranjero'),
    )

    nombre_fantasia = models.CharField(max_length=100, db_column='nombre_fantasia', null=True, blank=True)
    es_proveedor_estado = models.BooleanField(db_column='es_proveedor_estado', default=False)
    es_contribuyente = models.BooleanField(db_column='es_contribuyente', default=False, help_text='El documento es un RUC')
    es_persona_juridica = models.BooleanField(db_column='es_persona_juridica', default=False)
    tipo_documento = models.IntegerField(db_column='tipo_documento', choices=TIPOS_DOCUMENTO, default=TIPO_DOC_CEDULA_PARAGUAYA)
    numero_casa = models.IntegerField(db_column='numero_casa', default=0)
    id_ciudad = models.ForeignKey(Ciudad, models.DO_NOTHING, db_column='id_ciudad', null=True, blank=True)
    pais = models.ForeignKey(Pais, models.DO_NOTHING, db_column='pais', null=True, blank=True)
    tipo_operacion = models.CharField(max_length=3, db_column='tipo_operacion', choices=TIPOS_OPERACION, default=OPERACION_B2C)

    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def calcular_tipo_operacion(self):
        if self.es_proveedor_estado:
            return self.OPERACION_B2G
        if self.tipo_documento in self.TIPOS_DOCUMENTO_EXTRANJERO:
            return self.OPERACION_B2F
        if self.es_contribuyente and self.es_persona_juridica:
            return self.OPERACION_B2B
        return self.OPERACION_B2C

    def save(self, *args, **kwargs):
        self.tipo_operacion = self.calcular_tipo_operacion()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'IdCliente: {self.id_cliente} , Cliente {self.nombre}'
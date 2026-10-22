import calendar
from datetime import date

from django.db import models

from apps.clientes.models import Cliente
from apps.ventas.models import Venta

MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)


def nombre_mes(mes):
    return MESES[mes - 1]


class Contrato(models.Model):
    PERIODICIDAD_MENSUAL = "MENSUAL"
    PERIODICIDAD_ANUAL = "ANUAL"
    PERIODICIDADES = (
        (PERIODICIDAD_MENSUAL, "Mensual"),
        (PERIODICIDAD_ANUAL, "Anual"),
    )

    id_contrato = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(Cliente, models.DO_NOTHING, db_column="id_cliente")
    descripcion = models.CharField(max_length=120, db_column="descripcion")
    # Texto largo que se imprime al pie del KuDE (garantias, condiciones, etc.).
    observacion = models.TextField(db_column="observacion", blank=True, default="")
    periodicidad = models.CharField(max_length=10, choices=PERIODICIDADES, default=PERIODICIDAD_MENSUAL)
    fecha_inicio = models.DateField(db_column="fecha_inicio")
    fecha_fin = models.DateField(db_column="fecha_fin", null=True, blank=True)
    activo = models.BooleanField(default=True)
    usuario_creacion = models.IntegerField(db_column="usuario_creacion", null=True, blank=True)
    usuario_modificacion = models.IntegerField(db_column="usuario_modificacion", null=True, blank=True)
    fecha_creacion = models.DateTimeField(db_column="fecha_creacion", auto_now_add=True)
    fecha_modificacion = models.DateTimeField(db_column="fecha_modificacion", null=True, blank=True)

    class Meta:
        db_table = "contratos_alquiler"
        verbose_name = "Contrato de alquiler"
        verbose_name_plural = "Contratos de alquiler"

    def __str__(self):
        return f"Contrato {self.id_contrato} - {self.descripcion}"

    def periodo_de(self, anio, mes):
        """Devuelve la fecha de inicio del periodo a facturar en anio/mes, o
        None si el contrato no se factura ese mes."""
        primer_dia = date(anio, mes, 1)
        ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])
        if self.fecha_inicio > ultimo_dia:
            return None
        if self.fecha_fin and self.fecha_fin < primer_dia:
            return None
        # Los contratos anuales se facturan en el mes de aniversario del inicio.
        if self.periodicidad == self.PERIODICIDAD_ANUAL and self.fecha_inicio.month != mes:
            return None
        return primer_dia

    def etiqueta_periodo(self, periodo):
        if self.periodicidad == self.PERIODICIDAD_ANUAL:
            fin_mes = periodo.month - 1 or 12
            fin_anio = periodo.year + 1 if periodo.month > 1 else periodo.year
            return f"{nombre_mes(periodo.month)} {periodo.year} a {nombre_mes(fin_mes)} {fin_anio}"
        return f"{nombre_mes(periodo.month)} {periodo.year}"

    def completar_texto(self, texto, periodo):
        """Reemplaza {periodo}, {mes} y {anio} en las descripciones del contrato."""
        return (
            texto.replace("{periodo}", self.etiqueta_periodo(periodo))
            .replace("{mes}", nombre_mes(periodo.month))
            .replace("{anio}", str(periodo.year))
        )


class ConceptoContrato(models.Model):
    TIPO_ALQUILER = "ALQUILER"
    TIPO_GARANTIA = "GARANTIA"
    TIPO_OTRO = "OTRO"
    TIPOS = (
        (TIPO_ALQUILER, "Alquiler"),
        (TIPO_GARANTIA, "Garantía"),
        (TIPO_OTRO, "Otro"),
    )

    IVAS = (
        (10, "IVA 10%"),
        (5, "IVA 5%"),
        (0, "Exenta"),
    )

    id_concepto = models.AutoField(primary_key=True)
    id_contrato = models.ForeignKey(
        Contrato, models.CASCADE, db_column="id_contrato", related_name="conceptos"
    )
    tipo = models.CharField(max_length=10, choices=TIPOS, default=TIPO_ALQUILER)
    # SIFEN limita la descripcion del item a 120 caracteres; el detalle largo va en observacion.
    descripcion = models.CharField(max_length=120, db_column="descripcion")
    observacion = models.TextField(db_column="observacion", blank=True, default="")
    monto = models.PositiveBigIntegerField(db_column="monto", help_text="Monto en Gs. con IVA incluido")
    iva = models.PositiveSmallIntegerField(db_column="iva", choices=IVAS, default=10)
    # Ej. el deposito de garantia: se cobra en la primera factura del contrato.
    cobro_unico = models.BooleanField(db_column="cobro_unico", default=False)

    class Meta:
        db_table = "contratos_alquiler_concepto"
        verbose_name = "Concepto de contrato"
        verbose_name_plural = "Conceptos de contrato"
        ordering = ["id_concepto"]

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.descripcion}"


class FacturaAlquiler(models.Model):
    """Registra que periodo de un contrato se facturo y con que venta."""

    id_factura_alquiler = models.AutoField(primary_key=True)
    id_contrato = models.ForeignKey(
        Contrato, models.DO_NOTHING, db_column="id_contrato", related_name="facturaciones"
    )
    periodo = models.DateField(db_column="periodo")
    id_venta = models.OneToOneField(
        Venta, models.CASCADE, db_column="id_venta", related_name="factura_alquiler"
    )
    fecha_creacion = models.DateTimeField(db_column="fecha_creacion", auto_now_add=True)

    class Meta:
        db_table = "contratos_alquiler_factura"
        verbose_name = "Factura de alquiler"
        verbose_name_plural = "Facturas de alquiler"

    def __str__(self):
        return f"{self.id_contrato} - {self.periodo:%m/%Y}"

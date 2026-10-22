from django.contrib import admin

from .models import ConceptoContrato, Contrato, FacturaAlquiler


class ConceptoContratoInline(admin.TabularInline):
    model = ConceptoContrato
    extra = 0


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ("id_contrato", "descripcion", "id_cliente", "periodicidad", "activo")
    list_filter = ("periodicidad", "activo")
    inlines = [ConceptoContratoInline]


@admin.register(FacturaAlquiler)
class FacturaAlquilerAdmin(admin.ModelAdmin):
    list_display = ("id_contrato", "periodo", "id_venta", "fecha_creacion")

"""Facturacion periodica de los contratos de alquiler.

Cada factura se arma como una Venta con una linea por concepto del contrato
(descripcion, observacion e IVA propios) y se emite con el flujo normal de
facturas (numeracion, FacturaSend, KuDE, anulacion).
"""
from django.db import transaction
from django.utils import timezone

from apps.factura.emision import crear_factura
from apps.factura.models import Factura
from apps.ventas.models import Venta, VentaDetalle, VentaTipoDePago

from .models import Contrato, FacturaAlquiler


class FacturacionError(Exception):
    """El contrato no se puede facturar (ej. sin conceptos o ya facturado)."""


def facturaciones_vigentes(contrato):
    """Periodos del contrato con factura emitida (las anuladas no cuentan)."""
    return FacturaAlquiler.objects.filter(
        id_contrato=contrato, id_venta__factura__estado=Factura.ESTADO_EMITIDA
    )


def periodo_facturado(contrato, periodo):
    return facturaciones_vigentes(contrato).filter(periodo=periodo).first()


def conceptos_a_facturar(contrato):
    """Conceptos que corresponden a la proxima factura: los de cobro unico
    (ej. deposito de garantia) solo entran si el contrato nunca se facturo."""
    conceptos = list(contrato.conceptos.all())
    if facturaciones_vigentes(contrato).exists():
        conceptos = [c for c in conceptos if not c.cobro_unico]
    return conceptos


def contratos_del_periodo(anio, mes):
    """Devuelve [(contrato, periodo, factura_alquiler_o_None)] de los contratos
    activos que se facturan en anio/mes."""
    resultado = []
    contratos = (
        Contrato.objects.filter(activo=True)
        .select_related("id_cliente")
        .prefetch_related("conceptos")
        .order_by("id_cliente__nombre", "descripcion")
    )
    for contrato in contratos:
        periodo = contrato.periodo_de(anio, mes)
        if periodo:
            resultado.append((contrato, periodo, periodo_facturado(contrato, periodo)))
    return resultado


def _iva_incluido(monto, iva):
    if iva == 10:
        return round(monto / 11)
    if iva == 5:
        return round(monto / 21)
    return 0


def facturar_contrato(contrato, periodo, configuracion, usuario_id, tipo_pago, montos=None):
    """Crea la venta y la factura del periodo, cobrada al contado con `tipo_pago`.
    `montos` permite reemplazar el monto de algun concepto solo para esta
    factura ({id_concepto: monto}).

    Devuelve la Factura creada (todavia sin enviar a FacturaSend).
    """
    montos = montos or {}
    producto = configuracion.producto_alquiler
    if not producto:
        raise FacturacionError(
            "Configura el producto base de alquileres en Configuración Empresa."
        )

    lineas = []
    for concepto in conceptos_a_facturar(contrato):
        monto = montos.get(concepto.id_concepto, concepto.monto)
        if monto > 0:
            lineas.append((concepto, monto))
    if not lineas:
        raise FacturacionError(f'El contrato "{contrato.descripcion}" no tiene montos a facturar.')

    total_iva_10 = sum(_iva_incluido(m, c.iva) for c, m in lineas if c.iva == 10)
    total_iva_5 = sum(_iva_incluido(m, c.iva) for c, m in lineas if c.iva == 5)
    total = sum(m for _, m in lineas)

    with transaction.atomic():
        # Bloquea el contrato para no facturar dos veces el mismo periodo.
        Contrato.objects.select_for_update().get(pk=contrato.pk)
        if periodo_facturado(contrato, periodo):
            raise FacturacionError(
                f'El contrato "{contrato.descripcion}" ya tiene factura para {contrato.etiqueta_periodo(periodo)}.'
            )

        venta = Venta.objects.create(
            fecha_venta=timezone.now(),
            total_iva_10=total_iva_10,
            total_iva_5=total_iva_5,
            total_venta=total,
            usuario_creacion=usuario_id,
            id_cliente=contrato.id_cliente,
            observacion=contrato.completar_texto(contrato.observacion, periodo),
        )
        for concepto, monto in lineas:
            VentaDetalle.objects.create(
                id_venta=venta,
                id_producto=producto,
                cantidad_producto=1,
                total_detalle=monto,
                total_iva_10=_iva_incluido(monto, concepto.iva) if concepto.iva == 10 else 0,
                total_iva_5=_iva_incluido(monto, concepto.iva) if concepto.iva == 5 else 0,
                descripcion=contrato.completar_texto(concepto.descripcion, periodo)[:120],
                observacion=contrato.completar_texto(concepto.observacion, periodo),
                iva=concepto.iva,
            )
        VentaTipoDePago.objects.create(id_venta=venta, id_tipo_pago=tipo_pago, monto=total)
        FacturaAlquiler.objects.create(id_contrato=contrato, periodo=periodo, id_venta=venta)

        return crear_factura(
            venta,
            tipo_factura=Factura.TIPO_CONTADO,
            tipo_transaccion=Factura.TRANSACCION_SERVICIOS,
        )


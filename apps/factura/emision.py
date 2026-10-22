"""Emision de facturas a partir de una Venta.

La usan la emision manual (factura/views.py) y la facturacion de alquileres.
"""
from django.db import transaction

from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.facturasend_service import enviar_documento
from apps.factura.models import Factura
from apps.ventas.models import VentaTipoDePago


def obtener_forma_pago_texto(venta):
    pagos = VentaTipoDePago.objects.filter(id_venta=venta).select_related('id_tipo_pago')
    if not pagos:
        return 'Sin forma de pago'

    partes = []
    for pago in pagos:
        partes.append(f"{pago.id_tipo_pago.descripcion}: {int(pago.monto)}")
    return ", ".join(partes)


def crear_factura(venta, tipo_factura=Factura.TIPO_CONTADO, tipo_transaccion=Factura.TRANSACCION_MERCADERIA):
    """Crea la Factura de la venta con el siguiente numero de la secuencia.

    La configuracion se bloquea durante la transaccion para que dos emisiones
    simultaneas no tomen el mismo numero.
    """
    with transaction.atomic():
        configuracion = ConfiguracionEmpresa.objects.select_for_update().first()
        factura = Factura.objects.create(
            nro_factura=configuracion.generar_nro_factura(),
            id_venta=venta,
            id_tipo=1 if tipo_factura == Factura.TIPO_CONTADO else 2,
            tipo_factura=tipo_factura,
            tipo_transaccion=tipo_transaccion,
            forma_pago=obtener_forma_pago_texto(venta),
            estado=Factura.ESTADO_EMITIDA,
            nombre_empresa=configuracion.nombre_empresa,
            ruc_empresa=configuracion.ruc,
            direccion_empresa=configuracion.direccion,
            nro_timbrado=configuracion.nro_timbrado,
            vigencia_timbrado_desde=configuracion.vigencia_timbrado_desde,
            vigencia_timbrado_hasta=configuracion.vigencia_timbrado_hasta,
        )
        configuracion.secuencia_actual += 1
        configuracion.save(update_fields=['secuencia_actual'])
    return factura


def enviar_si_corresponde(factura, configuracion):
    """Envia la factura a FacturaSend segun la configuracion.

    Devuelve (ok: bool, mensaje: str) listo para mostrar al usuario.
    """
    if not (configuracion.facturasend_url and configuracion.facturasend_api_key):
        return True, f'Factura {factura.nro_factura} emitida correctamente.'

    if not configuracion.facturasend_sincrono:
        # Comunicacion asincrona: queda pendiente para el comando "enviar_facturasend".
        return True, (
            f'Factura {factura.nro_factura} emitida correctamente. '
            'Se enviará a FacturaSend en el próximo envío por lotes.'
        )

    # Comunicacion sincrona: se envia ahora mismo y se espera la respuesta.
    ok, mensaje_fs = enviar_documento(factura, configuracion)
    if ok:
        return True, f'Factura {factura.nro_factura} emitida y enviada a FacturaSend.'
    return False, (
        f'Factura {factura.nro_factura} emitida localmente, pero no se pudo enviar a '
        f'FacturaSend: {mensaje_fs}'
    )

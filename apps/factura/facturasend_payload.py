"""Construye el JSON de un Documento Electronico (DE) para FacturaSend
a partir de una Factura del sistema.

Referencia de la estructura:
https://facturasend.com.py/documentacion/estructura-json-de-un-de/
https://facturasend.com.py/documentacion/crear-un-nuevo-documento-electronico/

Cubre solo tipoDocumento=1 (Factura electronica), al contado o a credito
simple, con items gravados por IVA (5% o 10%). No cubre notas de
credito/debito, exoneraciones de IVA, transporte ni moneda extranjera.
"""
from apps.ventas.models import VentaDetalle, VentaTipoDePago

TIPO_DOCUMENTO_FACTURA = 1

TIPO_OPERACION_API = {
    'B2B': 1,
    'B2C': 2,
    'B2G': 3,
    'B2F': 4,
}

# Persona fisica = 1, persona juridica = 2 (estandar SIFEN).
TIPO_CONTRIBUYENTE_FISICA = 1
TIPO_CONTRIBUYENTE_JURIDICA = 2

# FacturaSend no tiene un codigo propio para "efectivo/tarjeta/transferencia":
# usa los codigos de condicion de pago de SIFEN. Los tipos de pago del
# sistema son texto libre, asi que se mapean por nombre con un valor por
# defecto. Ajustar esta tabla si se agregan nuevos tipos de pago.
TIPO_PAGO_SIFEN = {
    'efectivo': 1,
    'cheque': 2,
    'tarjeta de credito': 3,
    'tarjeta de debito': 4,
    'pos': 3,  # Se asume tarjeta de credito; revisar si en el negocio es debito.
    'transferencia': 5,
    'billetera electronica': 8,
}

PRESENCIA_OPERACION_PRESENCIAL = 1


class PayloadError(Exception):
    """Datos del sistema insuficientes para armar un DE valido (ej. cliente sin ciudad)."""


def _tipo_pago_sifen(descripcion):
    return TIPO_PAGO_SIFEN.get(descripcion.strip().lower(), 1)


def _cliente_payload(cliente):
    if not cliente.id_ciudad_id:
        raise PayloadError(
            f'El cliente "{cliente.nombre} {cliente.apellido}" no tiene ciudad asignada; '
            'es obligatoria para enviar el documento a FacturaSend.'
        )
    ciudad = cliente.id_ciudad
    distrito = ciudad.distrito
    departamento = distrito.departamento

    data = {
        'contribuyente': cliente.es_contribuyente,
        'razonSocial': f'{cliente.nombre} {cliente.apellido}'.strip(),
        'tipoOperacion': TIPO_OPERACION_API[cliente.tipo_operacion],
        'direccion': cliente.direccion or '',
        'numeroCasa': cliente.numero_casa,
        'departamento': departamento.codigo,
        'departamentoDescripcion': departamento.descripcion,
        'distrito': distrito.codigo,
        'distritoDescripcion': distrito.descripcion,
        'ciudad': ciudad.codigo,
        'ciudadDescripcion': ciudad.descripcion,
        'pais': cliente.pais_id or 'PRY',
        'paisDescripcion': cliente.pais.nombre if cliente.pais_id else 'Paraguay',
        'telefono': cliente.celular or '',
        'celular': cliente.celular or '',
        'email': cliente.correo or '',
        'codigo': str(cliente.id_cliente),
    }
    if cliente.nombre_fantasia:
        data['nombreFantasia'] = cliente.nombre_fantasia

    if cliente.es_contribuyente:
        data['ruc'] = cliente.documento
        data['tipoContribuyente'] = (
            TIPO_CONTRIBUYENTE_JURIDICA if cliente.es_persona_juridica else TIPO_CONTRIBUYENTE_FISICA
        )
    else:
        data['documentoTipo'] = cliente.tipo_documento
        data['documentoNumero'] = cliente.documento

    return data


def _items_payload(venta):
    detalles = (
        VentaDetalle.objects.filter(id_venta=venta)
        .select_related('id_producto', 'id_producto__id_medida', 'id_producto__id_iva')
    )
    items = []
    for detalle in detalles:
        producto = detalle.id_producto
        if not producto.id_medida.codigo_set:
            raise PayloadError(
                f'La medida "{producto.id_medida.descripcion}" del producto "{producto.nombre}" '
                'no tiene codigo_set asignado (tabla de unidades de medida de la SET).'
            )
        if detalle.cantidad_producto == 0:
            raise PayloadError(f'El producto "{producto.nombre}" tiene cantidad 0 en la venta.')

        iva_descripcion = (producto.id_iva.descripcion or '').strip()
        iva_porcentaje = int(iva_descripcion) if iva_descripcion.isdigit() else 0
        gravado = iva_porcentaje > 0

        items.append({
            'codigo': str(producto.id_producto),
            'descripcion': producto.nombre,
            'unidadMedida': producto.id_medida.codigo_set,
            'cantidad': detalle.cantidad_producto,
            'precioUnitario': round(detalle.total_detalle / detalle.cantidad_producto, 2),
            'ivaTipo': 1 if gravado else 4,  # 1=Gravado IVA, 4=Exento
            'ivaProporcion': 100 if gravado else 0,
            'iva': iva_porcentaje,
        })
    if not items:
        raise PayloadError('La venta no tiene items; no se puede generar el DE.')
    return items


def _condicion_payload(factura, venta):
    pagos = VentaTipoDePago.objects.filter(id_venta=venta).select_related('id_tipo_pago')
    entregas = [
        {
            'tipo': _tipo_pago_sifen(pago.id_tipo_pago.descripcion),
            'monto': pago.monto,
            'moneda': 'PYG',
        }
        for pago in pagos
    ]
    if not entregas:
        # Nunca deberia pasar (la venta exige forma de pago), pero evita un DE invalido.
        entregas = [{'tipo': 1, 'monto': venta.total_venta, 'moneda': 'PYG'}]

    condicion = {'tipo': 1 if factura.tipo_factura == factura.TIPO_CONTADO else 2}
    if condicion['tipo'] == 1:
        condicion['entregas'] = entregas
    else:
        # Credito simple a un solo plazo; el sistema no maneja cuotas todavia.
        condicion['credito'] = {
            'tipo': 1,
            'plazo': 30,
            'infoCuotas': [{'moneda': 'PYG', 'monto': venta.total_venta}],
        }
    return condicion


def construir_documento(factura):
    """Devuelve el dict de un DE (tipoDocumento=1) listo para `crear_documento`.

    Puede levantar PayloadError si al cliente, al producto o a la medida
    les falta un dato obligatorio para SIFEN.
    """
    venta = factura.id_venta
    cliente = venta.id_cliente

    try:
        establecimiento, punto, numero = factura.nro_factura.split('-')
    except ValueError as exc:
        raise PayloadError(f'nro_factura "{factura.nro_factura}" no tiene el formato PPP-SSS-NNNNNNN.') from exc

    return {
        'tipoDocumento': TIPO_DOCUMENTO_FACTURA,
        'establecimiento': establecimiento,
        'punto': punto,
        'numero': numero,
        'fecha': factura.fecha_emision.strftime('%Y-%m-%dT%H:%M:%S'),
        'tipoEmision': 1,  # Normal
        'tipoTransaccion': 1,  # Venta de mercaderia
        'tipoImpuesto': 1,  # IVA
        'moneda': 'PYG',
        'cliente': _cliente_payload(cliente),
        'factura': {'presencia': PRESENCIA_OPERACION_PRESENCIAL},
        'condicion': _condicion_payload(factura, venta),
        'items': _items_payload(venta),
    }

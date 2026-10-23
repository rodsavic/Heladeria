"""Construye el JSON de un Documento Electronico (DE) para FacturaSend
a partir de una Factura del sistema.
Cubre solo tipoDocumento=1 (Factura electronica), al contado o a credito
simple, con items gravados por IVA (5% o 10%) o exentos. Los items pueden
traer descripcion, observacion e IVA propios (lineas de alquiler). No cubre notas de
credito/debito, exoneraciones de IVA, transporte ni moneda extranjera.
"""
from django.utils import timezone

from apps.clientes.models import Cliente
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

TIPO_PAGO_CHEQUE = 2
TIPOS_PAGO_TARJETA = (3, 4)

# infoTarjeta: el sistema no registra la marca de la tarjeta, se informa
# 99=Otro con la descripcion del tipo de pago, procesada por POS.
TARJETA_DENOMINACION_OTRO = 99
TARJETA_MEDIO_PAGO_POS = 1

PRESENCIA_OPERACION_PRESENCIAL = 1

# Afectacion tributaria del item (ivaTipo, campo E731).
IVA_TIPO_GRAVADO = 1
IVA_TIPO_EXENTO = 3

# Con tipoOperacion=3 (B2G) SIFEN exige los datos de contratacion de la DNCP;
# si la venta no viene de una licitacion se pueden informar en cero.
DNCP_SIN_LICITACION = {
    'modalidad': '00',
    'entidad': 0,
    'año': 0,
    'secuencia': 0,
}

RAZON_SOCIAL_INNOMINADO = 'Sin Nombre'


class PayloadError(Exception):
    """Datos del sistema insuficientes para armar un DE valido (ej. cliente sin ciudad)."""


def _tipo_pago_sifen(descripcion):
    return TIPO_PAGO_SIFEN.get(descripcion.strip().lower(), 1)


def _cliente_payload(cliente):
    tipo_operacion = TIPO_OPERACION_API[cliente.tipo_operacion]
    innominado = not cliente.es_contribuyente and cliente.tipo_documento == Cliente.TIPO_DOC_INNOMINADO
    razon_social = f'{cliente.nombre} {cliente.apellido}'.strip()

    data = {
        'contribuyente': cliente.es_contribuyente,
        'razonSocial': RAZON_SOCIAL_INNOMINADO if innominado or not razon_social else razon_social,
        'tipoOperacion': tipo_operacion,
        'pais': cliente.pais_id or 'PRY',
        'paisDescripcion': cliente.pais.nombre if cliente.pais_id else 'Paraguay',
        # SIFEN pide de 3 a 15 caracteres: se rellena con ceros (13 -> "013").
        'codigo': str(cliente.id_cliente).zfill(3),
    }

    # La direccion del receptor es opcional en SIFEN, pero si se informa
    # exige departamento/distrito/ciudad: solo se manda con ciudad asignada.
    # Para B2F (extranjero) la direccion es obligatoria y no se informan
    # departamento/distrito/ciudad.
    if tipo_operacion == TIPO_OPERACION_API['B2F']:
        if not cliente.direccion:
            raise PayloadError(
                f'El cliente "{razon_social}" es extranjero (B2F): la dirección es obligatoria para SIFEN.'
            )
        data['direccion'] = cliente.direccion
        data['numeroCasa'] = cliente.numero_casa
    elif cliente.id_ciudad_id and cliente.direccion:
        ciudad = cliente.id_ciudad
        distrito = ciudad.distrito
        departamento = distrito.departamento
        data.update({
            'direccion': cliente.direccion,
            'numeroCasa': cliente.numero_casa,
            'departamento': departamento.codigo,
            'departamentoDescripcion': departamento.descripcion,
            'distrito': distrito.codigo,
            'distritoDescripcion': distrito.descripcion,
            'ciudad': ciudad.codigo,
            'ciudadDescripcion': ciudad.descripcion,
        })

    # SIFEN valida el largo: telefono 6-15 y celular 10-20 caracteres. Valores
    # de relleno ("NA", "123") se omiten en vez de hacer rechazar el documento.
    numero = (cliente.celular or '').strip()
    if any(c.isdigit() for c in numero):
        if 6 <= len(numero) <= 15:
            data['telefono'] = numero
        if 10 <= len(numero) <= 20:
            data['celular'] = numero
    if cliente.correo:
        data['email'] = cliente.correo

    if cliente.nombre_fantasia:
        data['nombreFantasia'] = cliente.nombre_fantasia

    if cliente.es_contribuyente:
        if '-' not in (cliente.documento or ''):
            raise PayloadError(
                f'El RUC "{cliente.documento}" del cliente "{razon_social}" debe incluir el dígito '
                'verificador (formato 1234567-8).'
            )
        data['ruc'] = cliente.documento
        data['tipoContribuyente'] = (
            TIPO_CONTRIBUYENTE_JURIDICA if cliente.es_persona_juridica else TIPO_CONTRIBUYENTE_FISICA
        )
    else:
        data['documentoTipo'] = cliente.tipo_documento
        # En un DE innominado el numero de documento se completa con 0.
        data['documentoNumero'] = '0' if innominado else cliente.documento
        if cliente.tipo_documento == Cliente.TIPO_DOC_OTRO:
            data['documentoTipoDescripcion'] = 'Otro'

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

        # La linea puede traer su propio IVA (ej. alquileres); si no, se usa el del producto.
        if detalle.iva is not None:
            iva_descripcion = str(detalle.iva)
        else:
            iva_descripcion = (producto.id_iva.descripcion or '').strip()
        iva_porcentaje = int(iva_descripcion) if iva_descripcion.isdigit() else 0
        if iva_porcentaje not in (0, 5, 10):
            raise PayloadError(
                f'La tasa de IVA "{iva_descripcion}" del producto "{producto.nombre}" no es válida '
                '(SIFEN admite 0, 5 o 10).'
            )
        gravado = iva_porcentaje > 0

        item = {
            'codigo': str(producto.id_producto),
            # SIFEN limita la descripcion del item (E708) a 120 caracteres; el
            # texto largo va en "observacion" (E714).
            'descripcion': (detalle.descripcion or producto.nombre)[:120],
            'unidadMedida': producto.id_medida.codigo_set,
            'cantidad': detalle.cantidad_producto,
            'precioUnitario': round(detalle.total_detalle / detalle.cantidad_producto, 2),
            'ivaTipo': IVA_TIPO_GRAVADO if gravado else IVA_TIPO_EXENTO,
            # Antes se llamaba "ivaBase"; FacturaSend lo sigue aceptando por compatibilidad.
            'ivaProporcion': 100 if gravado else 0,
            'iva': iva_porcentaje,
        }
        if detalle.observacion:
            item['observacion'] = detalle.observacion
        items.append(item)
    if not items:
        raise PayloadError('La venta no tiene items; no se puede generar el DE.')
    return items


def _descripcion_tarjeta(descripcion):
    """SIFEN exige de 4 a 20 caracteres en infoTarjeta.tipoDescripcion
    (ej. "POS" es muy corto y se informa como "Tarjeta POS")."""
    descripcion = descripcion.strip()
    if len(descripcion) < 4:
        descripcion = f'Tarjeta {descripcion}'.strip()
    return descripcion[:20]


def _entrega_payload(pago):
    descripcion = pago.id_tipo_pago.descripcion
    tipo = _tipo_pago_sifen(descripcion)
    entrega = {'tipo': tipo, 'monto': pago.monto, 'moneda': 'PYG'}

    if tipo in TIPOS_PAGO_TARJETA:
        # infoTarjeta es obligatorio para pagos con tarjeta de credito/debito.
        entrega['infoTarjeta'] = {
            'tipo': TARJETA_DENOMINACION_OTRO,
            'tipoDescripcion': _descripcion_tarjeta(descripcion),
            'medioPago': TARJETA_MEDIO_PAGO_POS,
        }
    elif tipo == TIPO_PAGO_CHEQUE:
        # infoCheque (numero y banco) es obligatorio y el sistema no lo registra.
        raise PayloadError(
            'El pago con cheque requiere número de cheque y banco para SIFEN, y la venta no los tiene.'
        )
    return entrega


def _condicion_payload(factura, venta):
    pagos = VentaTipoDePago.objects.filter(id_venta=venta).select_related('id_tipo_pago')
    entregas = [_entrega_payload(pago) for pago in pagos]
    if not entregas:
        # Nunca deberia pasar (la venta exige forma de pago), pero evita un DE invalido.
        entregas = [{'tipo': 1, 'monto': venta.total_venta, 'moneda': 'PYG'}]

    condicion = {'tipo': 1 if factura.tipo_factura == factura.TIPO_CONTADO else 2}
    if condicion['tipo'] == 1:
        condicion['entregas'] = entregas
    else:
        # Credito simple a un solo plazo (tipo 1); el sistema no maneja cuotas
        # todavia. infoCuotas solo corresponde a credito por cuotas (tipo 2).
        condicion['credito'] = {
            'tipo': 1,
            'plazo': '30 días',
        }
    return condicion


def separar_nro_factura(factura):
    """Devuelve (establecimiento, punto, numero) a partir de "PPP-SSS-NNNNNNN"."""
    try:
        establecimiento, punto, numero = factura.nro_factura.split('-')
    except ValueError as exc:
        raise PayloadError(f'nro_factura "{factura.nro_factura}" no tiene el formato PPP-SSS-NNNNNNN.') from exc
    return establecimiento, punto, numero


def construir_documento(factura):
    """Devuelve el dict de un DE (tipoDocumento=1) listo para `crear_documento`.

    Puede levantar PayloadError si al cliente, al producto o a la medida
    les falta un dato obligatorio para SIFEN.
    """
    venta = factura.id_venta
    cliente = venta.id_cliente

    establecimiento, punto, numero = separar_nro_factura(factura)

    # fecha_emision se guarda en UTC (USE_TZ=True); SIFEN espera la hora local
    # de Paraguay y rechaza fechas "adelantadas".
    fecha = factura.fecha_emision
    if timezone.is_aware(fecha):
        fecha = timezone.localtime(fecha)

    documento = {
        'tipoDocumento': TIPO_DOCUMENTO_FACTURA,
        'establecimiento': establecimiento,
        'punto': punto,
        'numero': numero,
        'fecha': fecha.strftime('%Y-%m-%dT%H:%M:%S'),
        'tipoEmision': 1,  # Normal
        'tipoTransaccion': factura.tipo_transaccion,  # 1=Mercaderia, 2=Servicios
        'tipoImpuesto': 1,  # IVA
        'moneda': 'PYG',
        'cliente': _cliente_payload(cliente),
        'factura': {'presencia': PRESENCIA_OPERACION_PRESENCIAL},
        'condicion': _condicion_payload(factura, venta),
        'items': _items_payload(venta),
    }

    # Informacion de interes del emisor (B005): se imprime en el KuDE.
    if venta.observacion:
        documento['observacion'] = venta.observacion

    if cliente.tipo_operacion == Cliente.OPERACION_B2G:
        documento['dncp'] = dict(DNCP_SIN_LICITACION, fecha=fecha.strftime('%Y-%m-%d'))

    # Si el DE ya fue rechazado, se reenvia con el mismo CDC (recomendado por
    # FacturaSend, sobre todo si el KuDE ya se entrego al cliente).
    if factura.cdc:
        documento['cdc'] = factura.cdc

    return documento

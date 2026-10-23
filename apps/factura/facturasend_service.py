"""Orquesta el envio de una Factura a FacturaSend: arma el payload, llama
a la API y guarda el resultado (cdc, estado_sifen, respuesta_sifen) en el
propio modelo Factura.

Uso tipico:
    ok, mensaje = enviar_documento(factura, configuracion)

No lanza excepciones hacia arriba: una falla de red, de datos o de la API
de FacturaSend se guarda en `factura.respuesta_sifen` y se devuelve en el
mensaje, para que la emision de la factura en el sistema nunca se pierda
por un problema de la integracion.
"""
import json
import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .facturasend_client import MAX_DOCUMENTOS_POR_LLAMADA, FacturaSendClient, FacturaSendError
from .facturasend_payload import TIPO_DOCUMENTO_FACTURA, PayloadError, construir_documento, separar_nro_factura
from .models import Factura

logger = logging.getLogger(__name__)

# SIFEN solo permite cancelar documentos aprobados dentro de las 48 horas.
PLAZO_CANCELACION = timedelta(hours=48)

# Estados que todavia esperan respuesta de SIFEN y hay que seguir consultando.
ESTADOS_SIFEN_PENDIENTES = (Factura.ESTADO_SIFEN_GENERADO, Factura.ESTADO_SIFEN_ENVIADO_LOTE)
ESTADOS_SIFEN_APROBADOS = (Factura.ESTADO_SIFEN_APROBADO, Factura.ESTADO_SIFEN_APROBADO_OBS)


def _parsear_estado(estado_texto):
    """FacturaSend devuelve el estado como texto, ej. "0-Generado" o
    "2-Aprobado". Se toma el codigo numerico inicial; si no se puede
    interpretar, se asume "Generado" (ya se confirmo la creacion del DE)."""
    try:
        return int(str(estado_texto).split('-', 1)[0])
    except (TypeError, ValueError):
        return Factura.ESTADO_SIFEN_GENERADO


def _mensaje_error(resultado):
    """FacturaSend manda un mensaje generico en `error` y el detalle real
    (por campo) en `errores`; se devuelven ambos para poder corregir el dato."""
    general = resultado.get('error') or 'Error desconocido de FacturaSend.'
    detalle = resultado.get('errores')
    if not detalle:
        return general
    if isinstance(detalle, list):
        detalle = '; '.join(
            str(e.get('error') or e) if isinstance(e, dict) else str(e) for e in detalle
        )
    return f'{general} Detalle: {detalle}'


def _buscar_clave(objeto, sufijo):
    """Busca recursivamente el primer valor cuya clave termine en `sufijo`.
    Los eventos devuelven la respuesta de SIFEN tal cual (con prefijos de
    namespace como "ns2:"), asi que no conviene depender de la ruta exacta."""
    if isinstance(objeto, dict):
        for clave, valor in objeto.items():
            if str(clave).endswith(sufijo) and not isinstance(valor, (dict, list)):
                return valor
            encontrado = _buscar_clave(valor, sufijo)
            if encontrado is not None:
                return encontrado
    elif isinstance(objeto, list):
        for valor in objeto:
            encontrado = _buscar_clave(valor, sufijo)
            if encontrado is not None:
                return encontrado
    return None


def _evento_aprobado(resultado):
    """Un evento solo es valido si `success` es true y SIFEN respondio
    dEstRes = "Aprobado". Devuelve (ok, mensaje_sifen)."""
    if not resultado.get('success'):
        return False, _mensaje_error(resultado)
    estado = _buscar_clave(resultado.get('result'), 'dEstRes')
    if str(estado).strip().lower() != 'aprobado':
        mensaje = _buscar_clave(resultado.get('result'), 'dMsgRes') or f'Estado del evento: {estado}'
        return False, mensaje
    return True, ''


def enviar_documento(factura, configuracion):
    """Envia la factura a FacturaSend y actualiza sus campos SIFEN.

    Si la factura ya tiene CDC (fue rechazada), se reenvia con el mismo CDC.

    Devuelve (ok: bool, mensaje: str).
    """
    try:
        documento = construir_documento(factura)
    except PayloadError as exc:
        factura.respuesta_sifen = f'No se pudo armar el documento: {exc}'
        factura.save(update_fields=['respuesta_sifen'])
        logger.warning('FacturaSend: payload invalido para factura %s: %s', factura.nro_factura, exc)
        return False, str(exc)

    try:
        cliente = FacturaSendClient(configuracion)
        resultado = cliente.crear_documento(documento)
    except FacturaSendError as exc:
        factura.respuesta_sifen = f'Error de comunicacion: {exc}'
        factura.save(update_fields=['respuesta_sifen'])
        logger.error('FacturaSend: error de comunicacion para factura %s: %s', factura.nro_factura, exc)
        return False, str(exc)

    factura.respuesta_sifen = json.dumps(resultado, ensure_ascii=False)

    if not resultado.get('success'):
        factura.save(update_fields=['respuesta_sifen'])
        error = _mensaje_error(resultado)
        logger.error('FacturaSend: rechazo para factura %s: %s', factura.nro_factura, error)
        return False, f'FacturaSend rechazó el documento: {error}'

    de_list = (resultado.get('result') or {}).get('deList') or []
    if not de_list:
        factura.save(update_fields=['respuesta_sifen'])
        return False, 'FacturaSend no devolvió información del documento generado.'

    de = de_list[0]
    factura.cdc = de.get('cdc', '')
    factura.estado_sifen = _parsear_estado(de.get('estado'))
    factura.save(update_fields=['cdc', 'estado_sifen', 'respuesta_sifen'])
    return True, f'Documento enviado a FacturaSend (CDC {factura.cdc}).'


def actualizar_estados(configuracion, facturas=None):
    """Consulta en FacturaSend (POST /de/estado) el estado de las facturas que
    siguen esperando respuesta de SIFEN y actualiza `estado_sifen`.

    FacturaSend recomienda llamarlo periodicamente (ej. cada 10 minutos)
    mientras existan documentos en 0-Generado, y no consultar los que ya
    tienen estado final (aprobado/rechazado).

    Devuelve (actualizadas: int, mensaje_error: str | None).
    """
    if facturas is None:
        facturas = Factura.objects.filter(estado_sifen__in=ESTADOS_SIFEN_PENDIENTES).exclude(cdc='')
    por_cdc = {f.cdc: f for f in facturas if f.cdc}
    if not por_cdc:
        return 0, None

    try:
        cliente = FacturaSendClient(configuracion)
    except FacturaSendError as exc:
        return 0, str(exc)

    cdcs = list(por_cdc)
    actualizadas = 0
    for inicio in range(0, len(cdcs), MAX_DOCUMENTOS_POR_LLAMADA):
        bloque = cdcs[inicio:inicio + MAX_DOCUMENTOS_POR_LLAMADA]
        try:
            resultado = cliente.consultar_estados(bloque)
        except FacturaSendError as exc:
            logger.error('FacturaSend: error al consultar estados: %s', exc)
            return actualizadas, str(exc)
        if not resultado.get('success'):
            return actualizadas, _mensaje_error(resultado)

        for de in resultado.get('deList') or []:
            factura = por_cdc.get(de.get('cdc'))
            if factura is None:
                continue
            situacion = de.get('situacion')
            nuevo_estado = situacion if isinstance(situacion, int) else _parsear_estado(de.get('estado'))
            factura.estado_sifen = nuevo_estado
            factura.respuesta_sifen = json.dumps(de, ensure_ascii=False)
            factura.save(update_fields=['estado_sifen', 'respuesta_sifen'])
            actualizadas += 1
    return actualizadas, None


def cancelar_documento(factura, configuracion, motivo):
    """Envia el evento de cancelacion. Solo aplica a documentos aprobados en
    SIFEN y dentro de las 48 horas desde su emision; pasado ese plazo hay
    que emitir una nota de credito."""
    if not factura.cdc:
        return False, 'La factura no tiene CDC: nunca se envió a FacturaSend.'
    if factura.estado_sifen not in ESTADOS_SIFEN_APROBADOS:
        return False, (
            f'Solo se pueden cancelar documentos aprobados por SIFEN '
            f'(estado actual: {factura.get_estado_sifen_display()}).'
        )
    if timezone.now() - factura.fecha_emision > PLAZO_CANCELACION:
        return False, (
            'Pasaron más de 48 horas desde la emisión: SIFEN ya no permite cancelar el documento. '
            'Debe emitirse una nota de crédito.'
        )

    try:
        cliente = FacturaSendClient(configuracion)
        resultado = cliente.cancelar(factura.cdc, motivo)
    except FacturaSendError as exc:
        logger.error('FacturaSend: error al cancelar factura %s: %s', factura.nro_factura, exc)
        return False, str(exc)

    factura.respuesta_sifen = json.dumps(resultado, ensure_ascii=False)
    ok, error = _evento_aprobado(resultado)
    if not ok:
        factura.save(update_fields=['respuesta_sifen'])
        return False, f'FacturaSend rechazó la cancelación: {error}'

    factura.estado_sifen = Factura.ESTADO_SIFEN_CANCELADO
    factura.save(update_fields=['estado_sifen', 'respuesta_sifen'])
    return True, 'Documento cancelado en FacturaSend.'


def inutilizar_numero(factura, configuracion, motivo):
    """Envia el evento de inutilizacion del numero de la factura. Corresponde
    cuando el numero del timbrado no se va a usar: factura anulada que nunca
    se aprobo en SIFEN (no enviada o rechazada)."""
    if factura.estado_sifen in ESTADOS_SIFEN_APROBADOS:
        return False, 'El documento está aprobado en SIFEN: debe cancelarse, no inutilizarse.'
    if factura.estado_sifen in ESTADOS_SIFEN_PENDIENTES and factura.cdc:
        return False, 'El documento todavía espera respuesta de SIFEN; consulte su estado antes de anularlo.'

    try:
        establecimiento, punto, numero = separar_nro_factura(factura)
    except PayloadError as exc:
        return False, str(exc)

    try:
        cliente = FacturaSendClient(configuracion)
        resultado = cliente.inutilizar(
            TIPO_DOCUMENTO_FACTURA, establecimiento, punto, int(numero), int(numero), motivo
        )
    except FacturaSendError as exc:
        logger.error('FacturaSend: error al inutilizar factura %s: %s', factura.nro_factura, exc)
        return False, str(exc)

    factura.respuesta_sifen = json.dumps(resultado, ensure_ascii=False)
    factura.save(update_fields=['respuesta_sifen'])
    ok, error = _evento_aprobado(resultado)
    if not ok:
        return False, f'FacturaSend rechazó la inutilización: {error}'
    return True, f'Número {factura.nro_factura} inutilizado en SIFEN.'


def _validar_emails(email):
    """Valida una o varias direcciones separadas por coma. Devuelve la cadena
    normalizada o levanta ValidationError."""
    direcciones = [d.strip() for d in email.split(',') if d.strip()]
    if not direcciones:
        raise ValidationError('Ingrese al menos una dirección de correo.')
    for direccion in direcciones:
        validate_email(direccion)
    return ', '.join(direcciones)


def reenviar_email(factura, configuracion, email=None):
    """Pide a FacturaSend que reenvie el correo con el KuDE y el XML. Sin
    `email` se envia a la direccion del cliente informada en el DE.

    Devuelve (ok: bool, mensaje: str).
    """
    if not factura.cdc:
        return False, 'La factura no tiene CDC: todavía no se envió a FacturaSend.'
    if factura.estado_sifen not in ESTADOS_SIFEN_APROBADOS:
        return False, 'Solo se envían por correo facturas aprobadas por SIFEN.'

    if email:
        try:
            email = _validar_emails(email)
        except ValidationError:
            return False, f'La dirección de correo "{email}" no es válida.'
    elif not factura.id_venta.id_cliente.correo:
        return False, 'El cliente no tiene correo cargado; indique una dirección de destino.'

    try:
        respuesta = FacturaSendClient(configuracion).reenviar_email([factura.cdc], email)
    except FacturaSendError as exc:
        return False, str(exc)

    # El endpoint no tiene respuesta documentada (el envio es asincrono); si
    # devuelve un JSON con success=false se informa el error. Ante un error
    # HTTP el cliente ya devuelve el JSON decodificado.
    resultado = respuesta
    if isinstance(respuesta, (bytes, bytearray)):
        try:
            resultado = json.loads(respuesta.decode('utf-8')) if respuesta else {}
        except ValueError:
            resultado = {}
    if isinstance(resultado, dict) and resultado.get('success') is False:
        return False, _mensaje_error(resultado)

    destino = email or factura.id_venta.id_cliente.correo
    return True, f'Se solicitó a FacturaSend el reenvío del correo a {destino}.'


def _envio_exitoso(envio):
    """Interpreta `ema_response` de un registro de envio: True si el servidor
    de correo lo acepto, False si fallo, None si no se puede saber."""
    respuesta = envio.get('ema_response')
    if isinstance(respuesta, str):
        try:
            respuesta = json.loads(respuesta)
        except ValueError:
            return None
    if isinstance(respuesta, dict) and 'success' in respuesta:
        return bool(respuesta['success'])
    return None


def consultar_envios_email(factura, configuracion):
    """Devuelve (envios: list[dict], mensaje_error | None) con el historial de
    correos enviados por FacturaSend para la factura, del mas reciente al
    mas antiguo. Cada envio trae fecha, destinatario, asunto y si fue exitoso."""
    if not factura.cdc:
        return [], None
    try:
        resultado = FacturaSendClient(configuracion).consultar_envios_email(factura.cdc)
    except FacturaSendError as exc:
        return [], str(exc)
    if not resultado.get('success'):
        return [], _mensaje_error(resultado)

    envios = []
    for envio in resultado.get('result') or []:
        fecha = parse_datetime(envio.get('ema_fecha') or '')
        envios.append({
            'fecha': timezone.localtime(fecha) if fecha else None,
            'destinatario': envio.get('ema_to') or '',
            'copia': envio.get('ema_cc') or '',
            'asunto': envio.get('ema_subject') or '',
            'exitoso': _envio_exitoso(envio),
            'respuesta': envio.get('ema_response') or '',
        })
    envios.sort(key=lambda e: e['fecha'] or timezone.now(), reverse=True)
    return envios, None


def verificar_envios_email(configuracion, max_reintentos=1, dias=7):
    """Revisa el envio de correo de las facturas aprobadas en los ultimos
    `dias` y reenvia las que fallaron, como maximo `max_reintentos` veces por
    factura (para no reenviar sin fin a una direccion invalida).

    - Si algun envio fue exitoso, la factura queda con email_verificado=True
      y no se vuelve a consultar.
    - Si hay envios y todos fallaron, se reenvia el correo.
    - Si todavia no hay envios, se espera a la proxima ejecucion (FacturaSend
      envia el correo al aprobarse el DE).

    Devuelve (verificadas, reenviadas, mensaje_error | None).
    """
    facturas = (
        Factura.objects.filter(
            estado=Factura.ESTADO_EMITIDA,
            estado_sifen__in=ESTADOS_SIFEN_APROBADOS,
            email_verificado=False,
            email_reintentos__lt=max_reintentos,
            fecha_emision__gte=timezone.now() - timedelta(days=dias),
        )
        .exclude(cdc='')
        .exclude(id_venta__id_cliente__correo='')
        .select_related('id_venta__id_cliente')
    )

    verificadas, reenviadas = 0, 0
    for factura in facturas:
        envios, error = consultar_envios_email(factura, configuracion)
        if error:
            return verificadas, reenviadas, error
        if not envios:
            continue
        if any(envio['exitoso'] for envio in envios):
            factura.email_verificado = True
            factura.save(update_fields=['email_verificado'])
            verificadas += 1
        elif all(envio['exitoso'] is False for envio in envios):
            ok, mensaje = reenviar_email(factura, configuracion)
            factura.email_reintentos += 1
            factura.save(update_fields=['email_reintentos'])
            if ok:
                reenviadas += 1
            else:
                logger.warning('FacturaSend: no se pudo reenviar el correo de %s: %s', factura.nro_factura, mensaje)
    return verificadas, reenviadas, None


def obtener_kude(factura, configuracion):
    """Descarga el PDF del KuDE (representacion impresa del DE, con CDC y QR).

    Devuelve (pdf_bytes | None, mensaje_error | None).
    """
    if not factura.cdc:
        return None, 'La factura no tiene CDC: todavía no se envió a FacturaSend.'
    try:
        contenido = FacturaSendClient(configuracion).obtener_kude_pdf([factura.cdc])
    except FacturaSendError as exc:
        return None, str(exc)

    if isinstance(contenido, (bytes, bytearray)) and contenido.startswith(b'%PDF'):
        return bytes(contenido), None
    # Si no vino un PDF, FacturaSend respondio un JSON de error.
    if isinstance(contenido, (bytes, bytearray)):
        try:
            contenido = json.loads(contenido.decode('utf-8'))
        except ValueError:
            return None, 'FacturaSend no devolvió un PDF válido.'
    if isinstance(contenido, dict):
        return None, _mensaje_error(contenido)
    return None, 'FacturaSend no devolvió un PDF válido.'

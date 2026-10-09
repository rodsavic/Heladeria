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

from .facturasend_client import FacturaSendClient, FacturaSendError
from .facturasend_payload import PayloadError, construir_documento
from .models import Factura

logger = logging.getLogger(__name__)


def _parsear_estado(estado_texto):
    """FacturaSend devuelve el estado como texto, ej. "0-Generado" o
    "2-Aprobado". Se toma el codigo numerico inicial; si no se puede
    interpretar, se asume "Generado" (ya se confirmo la creacion del DE)."""
    try:
        return int(str(estado_texto).split('-', 1)[0])
    except (TypeError, ValueError):
        return Factura.ESTADO_SIFEN_GENERADO


def enviar_documento(factura, configuracion):
    """Envia la factura a FacturaSend y actualiza sus campos SIFEN.

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
        error = resultado.get('error') or resultado.get('errores') or 'Error desconocido de FacturaSend.'
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


def cancelar_documento(factura, configuracion, motivo):
    """Envia el evento de cancelacion. Requiere que la factura ya tenga CDC
    (si nunca se envio a FacturaSend, no hay nada que cancelar alla)."""
    if not factura.cdc:
        return False, 'La factura no tiene CDC: nunca se envió a FacturaSend.'

    try:
        cliente = FacturaSendClient(configuracion)
        resultado = cliente.cancelar(factura.cdc, motivo)
    except FacturaSendError as exc:
        logger.error('FacturaSend: error al cancelar factura %s: %s', factura.nro_factura, exc)
        return False, str(exc)

    factura.respuesta_sifen = json.dumps(resultado, ensure_ascii=False)
    if not resultado.get('success'):
        factura.save(update_fields=['respuesta_sifen'])
        error = resultado.get('error') or resultado.get('errores') or 'Error desconocido de FacturaSend.'
        return False, f'FacturaSend rechazó la cancelación: {error}'

    factura.estado_sifen = Factura.ESTADO_SIFEN_CANCELADO
    factura.save(update_fields=['estado_sifen', 'respuesta_sifen'])
    return True, 'Documento cancelado en FacturaSend.'

import logging
import smtplib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils import timezone

from .facturasend_service import ESTADOS_SIFEN_APROBADOS, _validar_emails, obtener_kude, obtener_xml
from .gmail_api_backend import GmailApiError, gmail_api_configurada

logger = logging.getLogger(__name__)


def gmail_configurado():
    """True si hay cuenta remitente y credenciales: API de Gmail (OAuth) o SMTP."""
    if not settings.EMAIL_HOST_USER:
        return False
    return gmail_api_configurada() or bool(settings.EMAIL_HOST_PASSWORD)


def _cuerpo_correo(factura):
    venta = factura.id_venta
    cliente = venta.id_cliente
    total = f'{int(venta.total_venta):,}'.replace(',', '.')
    return (
        f'Estimado/a {cliente.nombre} {cliente.apellido}:\n\n'
        f'Adjuntamos la factura electrónica N° {factura.nro_factura} emitida por '
        f'{factura.nombre_empresa} (RUC {factura.ruc_empresa}).\n\n'
        f'Fecha de emisión: {timezone.localtime(factura.fecha_emision):%d/%m/%Y %H:%M}\n'
        f'Total: {total} Gs.\n'
        f'CDC: {factura.cdc}\n\n'
        'Puede verificar el documento en https://ekuatia.set.gov.py/consultas/ '
        'ingresando el CDC.\n\n'
        'Este es un correo automático, por favor no lo responda.\n'
    )


def enviar_factura_gmail(factura, configuracion, email=None):
    """Envia por Gmail el KuDE (y el XML si esta disponible) de la factura.
    Sin `email` se envia al correo del cliente.

    No lanza excepciones: devuelve (ok: bool, mensaje: str).
    """
    if not gmail_configurado():
        return False, (
            'El envío por Gmail no está configurado (EMAIL_HOST_USER y '
            'GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN o EMAIL_HOST_PASSWORD).'
        )
    if not factura.cdc:
        return False, 'La factura no tiene CDC: todavía no se envió a FacturaSend.'
    if factura.estado_sifen not in ESTADOS_SIFEN_APROBADOS:
        return False, 'Solo se envían por correo facturas aprobadas por SIFEN.'

    try:
        destino = _validar_emails(email or factura.id_venta.id_cliente.correo or '')
    except ValidationError:
        if email:
            return False, f'La dirección de correo "{email}" no es válida.'
        return False, 'El cliente no tiene un correo válido cargado; indique una dirección de destino.'

    pdf, error = obtener_kude(factura, configuracion)
    if error:
        return False, f'No se pudo obtener el KuDE de FacturaSend: {error}'

    # El XML es opcional: si falla, se envia igual el KuDE.
    xml, error_xml = obtener_xml(factura, configuracion)
    if error_xml:
        logger.warning('Gmail: no se pudo obtener el XML de %s: %s', factura.nro_factura, error_xml)

    mensaje = EmailMessage(
        subject=f'Factura electrónica {factura.nro_factura} - {factura.nombre_empresa}',
        body=_cuerpo_correo(factura),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[d.strip() for d in destino.split(',')],
    )
    mensaje.attach(f'KuDE-{factura.nro_factura}.pdf', pdf, 'application/pdf')
    if xml:
        mensaje.attach(f'{factura.cdc}.xml', xml, 'application/xml')

    try:
        mensaje.send(fail_silently=False)
    except (smtplib.SMTPException, OSError, GmailApiError) as exc:
        logger.error('Gmail: error al enviar la factura %s: %s', factura.nro_factura, exc)
        return False, f'Error al enviar por Gmail: {exc}'

    factura.fecha_email_respaldo = timezone.now()
    factura.save(update_fields=['fecha_email_respaldo'])

    adjuntos = 'KuDE y XML' if xml else 'KuDE (no se pudo obtener el XML)'
    return True, f'Factura enviada por Gmail a {destino} con {adjuntos}.'

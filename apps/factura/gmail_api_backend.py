"""Backend de correo de Django que envia por la API REST de Gmail (HTTPS).

Reemplaza al SMTP en servidores que bloquean los puertos 25/465/587 (ej.
Railway fuera del plan Pro, donde SMTP da "[Errno 101] Network is
unreachable"). Usa OAuth2 con un refresh token de la cuenta de Gmail; para
obtenerlo correr una vez en local:

    python manage.py gmail_autorizar

Variables de entorno: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
y EMAIL_HOST_USER (la cuenta de Gmail, usada como remitente).
"""
import base64
import json
import threading
import time
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

TOKEN_URL = 'https://oauth2.googleapis.com/token'
SEND_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
TIMEOUT_SEGUNDOS = 20

# El access token dura ~1 hora; se reutiliza entre envios.
_token_lock = threading.Lock()
_token = {'valor': None, 'vence': 0.0}


class GmailApiError(Exception):
    """Error al obtener el token o al enviar el mensaje por la API de Gmail."""


def gmail_api_configurada():
    return bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET and settings.GMAIL_REFRESH_TOKEN)


def _llamar(url, data, headers):
    req = urllib_request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib_request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
            return json.loads(resp.read().decode('utf-8') or '{}')
    except urllib_error.HTTPError as exc:
        cuerpo = exc.read().decode('utf-8', errors='replace')
        raise GmailApiError(f'Gmail respondió {exc.code}: {cuerpo[:300]}') from exc
    except urllib_error.URLError as exc:
        raise GmailApiError(f'No se pudo conectar con Gmail: {exc.reason}') from exc
    except ValueError as exc:
        raise GmailApiError('Gmail devolvió una respuesta no válida.') from exc


def _access_token():
    with _token_lock:
        if _token['valor'] and time.time() < _token['vence']:
            return _token['valor']
        datos = urllib_parse.urlencode({
            'client_id': settings.GMAIL_CLIENT_ID,
            'client_secret': settings.GMAIL_CLIENT_SECRET,
            'refresh_token': settings.GMAIL_REFRESH_TOKEN,
            'grant_type': 'refresh_token',
        }).encode('utf-8')
        respuesta = _llamar(TOKEN_URL, datos, {'Content-Type': 'application/x-www-form-urlencoded'})
        if 'access_token' not in respuesta:
            raise GmailApiError(f'Google no devolvió un access token: {respuesta}')
        _token['valor'] = respuesta['access_token']
        # Margen de un minuto antes del vencimiento real.
        _token['vence'] = time.time() + int(respuesta.get('expires_in', 3600)) - 60
        return _token['valor']


class GmailApiBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        enviados = 0
        try:
            token = _access_token()
            for mensaje in email_messages:
                if not mensaje.recipients():
                    continue
                crudo = base64.urlsafe_b64encode(mensaje.message().as_bytes(linesep='\r\n')).decode('ascii')
                _llamar(
                    SEND_URL,
                    json.dumps({'raw': crudo}).encode('utf-8'),
                    {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                )
                enviados += 1
        except GmailApiError:
            if not self.fail_silently:
                raise
        return enviados

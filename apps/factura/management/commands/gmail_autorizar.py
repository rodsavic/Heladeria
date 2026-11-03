"""Obtiene el refresh token de Gmail para el envio de correos por la API.

Se corre UNA vez en una PC con navegador (no en el servidor):

    python manage.py gmail_autorizar --client-id <id> --client-secret <secreto>

Abre el navegador para iniciar sesion con la cuenta de Gmail remitente y
autorizar el permiso "enviar correo". Al terminar imprime GMAIL_REFRESH_TOKEN
para cargarlo en las variables de entorno (Railway / .env).

El cliente OAuth debe ser de tipo "App de escritorio" en Google Cloud
Console, con la API de Gmail habilitada.
"""
import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.factura.gmail_api_backend import TOKEN_URL

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
SCOPE = 'https://www.googleapis.com/auth/gmail.send'


class _Receptor(BaseHTTPRequestHandler):
    """Recibe la redireccion de Google con el codigo de autorizacion."""
    parametros = {}

    def do_GET(self):
        _Receptor.parametros = dict(urllib_parse.parse_qsl(urllib_parse.urlparse(self.path).query))
        if 'code' not in _Receptor.parametros and 'error' not in _Receptor.parametros:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write('Listo, puede cerrar esta ventana y volver a la consola.'.encode('utf-8'))

    def log_message(self, *args):
        pass


class Command(BaseCommand):
    help = 'Autoriza la cuenta de Gmail y muestra el GMAIL_REFRESH_TOKEN para el envio por API.'

    def add_arguments(self, parser):
        parser.add_argument('--client-id', default=settings.GMAIL_CLIENT_ID)
        parser.add_argument('--client-secret', default=settings.GMAIL_CLIENT_SECRET)
        parser.add_argument('--puerto', type=int, default=8765)

    def handle(self, *args, **options):
        client_id, client_secret = options['client_id'], options['client_secret']
        if not client_id or not client_secret:
            raise CommandError('Indique --client-id y --client-secret (o GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET).')

        redirect_uri = f'http://127.0.0.1:{options["puerto"]}/'
        estado = secrets.token_urlsafe(16)
        url = f'{AUTH_URL}?' + urllib_parse.urlencode({
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': SCOPE,
            'access_type': 'offline',
            'prompt': 'consent',  # fuerza que Google devuelva el refresh token
            'state': estado,
        })

        self.stdout.write(f'Abriendo el navegador. Si no se abre, ingrese a:\n\n{url}\n')
        webbrowser.open(url)

        servidor = HTTPServer(('127.0.0.1', options['puerto']), _Receptor)
        while not ({'code', 'error'} & _Receptor.parametros.keys()):
            servidor.handle_request()
        servidor.server_close()

        parametros = _Receptor.parametros
        if 'error' in parametros:
            raise CommandError(f'Google rechazó la autorización: {parametros["error"]}')
        if parametros.get('state') != estado:
            raise CommandError('La respuesta de Google no corresponde a esta solicitud (state inválido).')

        datos = urllib_parse.urlencode({
            'code': parametros['code'],
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }).encode('utf-8')
        req = urllib_request.Request(TOKEN_URL, data=datos, method='POST',
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
        try:
            with urllib_request.urlopen(req, timeout=20) as resp:
                respuesta = json.loads(resp.read().decode('utf-8'))
        except urllib_error.HTTPError as exc:
            raise CommandError(f'Google respondió {exc.code}: {exc.read().decode("utf-8", "replace")}') from exc

        refresh_token = respuesta.get('refresh_token')
        if not refresh_token:
            raise CommandError(f'Google no devolvió un refresh token: {respuesta}')

        self.stdout.write(self.style.SUCCESS('\nAutorización correcta. Cargue estas variables de entorno:\n'))
        self.stdout.write(f'GMAIL_CLIENT_ID={client_id}')
        self.stdout.write(f'GMAIL_CLIENT_SECRET={client_secret}')
        self.stdout.write(f'GMAIL_REFRESH_TOKEN={refresh_token}')

"""Cliente HTTP minimo para la API REST de FacturaSend.

Referencia:
https://facturasend.com.py/documentacion/crear-un-nuevo-documento-electronico/
https://facturasend.com.py/documentacion/obtener-estado-actual-de-un-documento-electronico/
https://facturasend.com.py/documentacion/evento-de-cancelacion/

No se agrega la libreria `requests` como dependencia: se usa `urllib`
(incluido en Python) para no tocar requirements.txt.
"""
import json
from urllib import error as urllib_error
from urllib import request as urllib_request

TIMEOUT_SEGUNDOS = 20


class FacturaSendError(Exception):
    """Error de comunicacion con FacturaSend (red, timeout o respuesta no-JSON)."""


class FacturaSendClient:
    """Envuelve las llamadas REST a la API de FacturaSend para un tenant.

    `configuracion` es una instancia de ConfiguracionEmpresa, de donde se
    toman la URL base (incluye el tenantId, ej:
    "https://api.facturasend.com.py/<tenantId>") y la API Key.
    """

    def __init__(self, configuracion):
        if not configuracion.facturasend_url or not configuracion.facturasend_api_key:
            raise FacturaSendError('Falta configurar la URL o la API Key de FacturaSend.')
        self.base_url = configuracion.facturasend_url.rstrip('/')
        self.api_key = configuracion.facturasend_api_key

    def _headers(self):
        return {
            'Authorization': f'Bearer api_key_{self.api_key}',
            'Content-Type': 'application/json; charset=utf-8',
        }

    def _request(self, method, path, payload=None):
        url = f'{self.base_url}{path}'
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib_request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib_request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
                cuerpo = resp.read().decode('utf-8')
        except urllib_error.HTTPError as exc:
            # FacturaSend devuelve el detalle del error en el cuerpo, incluso con 4xx/5xx.
            cuerpo = exc.read().decode('utf-8')
            try:
                return json.loads(cuerpo)
            except ValueError:
                raise FacturaSendError(f'FacturaSend respondió {exc.code}: {cuerpo[:300]}') from exc
        except urllib_error.URLError as exc:
            raise FacturaSendError(f'No se pudo conectar con FacturaSend: {exc.reason}') from exc

        try:
            return json.loads(cuerpo)
        except ValueError as exc:
            raise FacturaSendError('FacturaSend devolvió una respuesta no válida (no es JSON).') from exc

    def crear_documento(self, documento):
        """POST /lote/create. `documento` es el dict de UN documento electrónico;
        la API siempre espera un array, aunque sea de un solo elemento."""
        return self._request('POST', '/lote/create', [documento])

    def consultar_estado(self, id_documento, cdc):
        """POST /de/estado/<id>/<cdc>. Actualiza y devuelve el estado real en SIFEN."""
        return self._request('POST', f'/de/estado/{id_documento}/{cdc}')

    def cancelar(self, cdc, motivo):
        """POST /evento/cancelacion."""
        return self._request('POST', '/evento/cancelacion', {'cdc': cdc, 'motivo': motivo})

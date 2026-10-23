"""Cliente HTTP minimo para la API REST de FacturaSend.
"""
import json
from urllib import error as urllib_error
from urllib import request as urllib_request

TIMEOUT_SEGUNDOS = 20

# Limite de documentos por llamada en /lote/create, /de/estado y /de/pdf.
MAX_DOCUMENTOS_POR_LLAMADA = 50


class FacturaSendError(Exception):
    """Error de comunicacion con FacturaSend (red, timeout o respuesta no-JSON)."""


class FacturaSendClient:
    """Envuelve las llamadas REST a la API de FacturaSend para un tenant.

    `configuracion` es una instancia de ConfiguracionEmpresa, de donde se
    toman la URL base (incluye el tenantId, ej:
    "https://api.facturasend.com.py/<tenantId>") y la API Key (que viene de
    la variable de entorno FACTURASEND_API_KEY).
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

    def _request(self, method, path, payload=None, binario=False):
        """Hace la llamada y devuelve el JSON decodificado, o los bytes crudos
        si `binario=True` (ej. el PDF del KuDE)."""
        url = f'{self.base_url}{path}'
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = urllib_request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib_request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
                cuerpo = resp.read()
        except urllib_error.HTTPError as exc:
            # FacturaSend devuelve el detalle del error en el cuerpo, incluso con 4xx/5xx.
            cuerpo = exc.read().decode('utf-8', errors='replace')
            try:
                return json.loads(cuerpo)
            except ValueError:
                raise FacturaSendError(f'FacturaSend respondió {exc.code}: {cuerpo[:300]}') from exc
        except urllib_error.URLError as exc:
            raise FacturaSendError(f'No se pudo conectar con FacturaSend: {exc.reason}') from exc

        if binario:
            return cuerpo
        try:
            return json.loads(cuerpo.decode('utf-8'))
        except ValueError as exc:
            raise FacturaSendError('FacturaSend devolvió una respuesta no válida (no es JSON).') from exc

    def crear_documento(self, documento):
        """POST /lote/create. `documento` es el dict de UN documento electrónico;
        la API siempre espera un array, aunque sea de un solo elemento."""
        return self._request('POST', '/lote/create', [documento])

    def consultar_estados(self, cdcs):
        """POST /de/estado. Devuelve el estado (y la respuesta de SIFEN) de
        hasta 50 CDCs. Es el metodo recomendado para seguir a los documentos
        enviados por lote mientras sigan en 0-Generado."""
        cuerpo = {'cdcList': [{'cdc': cdc} for cdc in cdcs]}
        return self._request('POST', '/de/estado', cuerpo)

    def consultar_por_cdc(self, cdc):
        """GET /de/cdc/<cdc>. Devuelve el registro de FacturaSend, incluido su `id`."""
        return self._request('GET', f'/de/cdc/{cdc}')

    def actualizar_estado(self, id_documento, cdc):
        """POST /de/estado/<id>/<cdc>. Fuerza a FacturaSend a volver a consultar
        en SIFEN un DE en 0-Generado o 4-Rechazado. `id_documento` es el id del
        registro en FacturaSend (se obtiene con `consultar_por_cdc`)."""
        return self._request('POST', f'/de/estado/{id_documento}/{cdc}')

    def cancelar(self, cdc, motivo):
        """POST /evento/cancelacion."""
        return self._request('POST', '/evento/cancelacion', {'cdc': cdc, 'motivo': motivo})

    def inutilizar(self, tipo_documento, establecimiento, punto, desde, hasta, motivo):
        """POST /evento/inutilizacion. Inutiliza el rango [desde, hasta] de la numeración."""
        return self._request('POST', '/evento/inutilizacion', {
            'tipoDocumento': tipo_documento,
            'establecimiento': establecimiento,
            'punto': punto,
            'desde': desde,
            'hasta': hasta,
            'motivo': motivo,
        })

    def reenviar_email(self, cdcs, email=None):
        """POST /de/email. Reenvia el correo (KuDE + XML) de los CDCs. Si se
        pasa `email` (solo con un unico CDC) se envia a esa direccion en vez
        de la del cliente. El envio es asincrono: la respuesta no confirma nada."""
        cuerpo = {'cdcList': [{'cdc': cdc} for cdc in cdcs]}
        if email:
            cuerpo['email'] = email
        return self._request('POST', '/de/email', cuerpo, binario=True)

    def consultar_envios_email(self, cdc):
        """GET /de/email/<cdc>. Historial de envios de correo del documento."""
        return self._request('GET', f'/de/email/{cdc}')

    def obtener_kude_pdf(self, cdcs):
        """POST /de/pdf. Devuelve los bytes del PDF del KuDE (hasta 50 CDCs)."""
        cuerpo = {'cdcList': [{'cdc': cdc} for cdc in cdcs]}
        return self._request('POST', '/de/pdf', cuerpo, binario=True)

from datetime import date
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings

from apps.clientes.models import Cliente
from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.correo_respaldo import enviar_factura_gmail
from apps.factura.facturasend_service import obtener_xml
from apps.factura.models import Factura
from apps.ventas.models import Venta

PDF = b'%PDF-1.4 kude'
XML = b'<?xml version="1.0"?><rDE></rDE>'
CDC = '0' * 44


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='heladeria@gmail.com',
    EMAIL_HOST_PASSWORD='clave-de-aplicacion',
    DEFAULT_FROM_EMAIL='heladeria@gmail.com',
    # Los tests no deben depender de las credenciales del .env local.
    GMAIL_CLIENT_ID='', GMAIL_CLIENT_SECRET='', GMAIL_REFRESH_TOKEN='',
)
class EnvioGmailTest(TestCase):
    def setUp(self):
        self.configuracion = ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa', ruc='80000000-1', direccion='Asunción', nro_timbrado='12345678',
            vigencia_timbrado_desde=date(2026, 1, 1),
            facturasend_url='https://api.facturasend.com.py/tenant',
        )
        cliente = Cliente.objects.create(
            documento='1234567', nombre='Juan', apellido='Pérez', correo='juan@correo.com', celular='',
        )
        venta = Venta.objects.create(
            total_iva_10=10_000, total_iva_5=0, total_venta=110_000, usuario_creacion=1, id_cliente=cliente,
        )
        self.factura = Factura.objects.create(
            nro_factura='001-001-0000001', id_venta=venta, nombre_empresa='Empresa', ruc_empresa='80000000-1',
            cdc=CDC, estado_sifen=Factura.ESTADO_SIFEN_APROBADO,
        )

    def _cliente(self, pdf=PDF, xml=XML):
        cliente = mock.patch('apps.factura.facturasend_service.FacturaSendClient').start()
        self.addCleanup(mock.patch.stopall)
        cliente.return_value.obtener_kude_pdf.return_value = pdf
        cliente.return_value.obtener_xml.return_value = xml
        return cliente

    def test_envia_kude_y_xml_al_cliente(self):
        self._cliente()
        ok, mensaje = enviar_factura_gmail(self.factura, self.configuracion)

        self.assertTrue(ok, mensaje)
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ['juan@correo.com'])
        self.assertIn('110.000 Gs.', correo.body)
        nombres = [adjunto[0] for adjunto in correo.attachments]
        self.assertEqual(nombres, ['KuDE-001-001-0000001.pdf', f'{CDC}.xml'])
        self.factura.refresh_from_db()
        self.assertIsNotNone(self.factura.fecha_email_respaldo)

    def test_sin_xml_envia_solo_kude(self):
        self._cliente(xml={'success': False, 'error': 'No encontrado'})
        ok, mensaje = enviar_factura_gmail(self.factura, self.configuracion, 'otro@correo.com')

        self.assertTrue(ok, mensaje)
        self.assertEqual(mail.outbox[0].to, ['otro@correo.com'])
        self.assertEqual(len(mail.outbox[0].attachments), 1)

    def test_sin_kude_no_envia(self):
        self._cliente(pdf={'success': False, 'error': 'Caído'})
        ok, _ = enviar_factura_gmail(self.factura, self.configuracion)

        self.assertFalse(ok)
        self.assertEqual(len(mail.outbox), 0)

    def test_factura_no_aprobada_no_envia(self):
        self.factura.estado_sifen = Factura.ESTADO_SIFEN_RECHAZADO
        ok, _ = enviar_factura_gmail(self.factura, self.configuracion)
        self.assertFalse(ok)

    @override_settings(EMAIL_HOST_PASSWORD='')
    def test_sin_configurar_no_envia(self):
        ok, mensaje = enviar_factura_gmail(self.factura, self.configuracion)
        self.assertFalse(ok)
        self.assertIn('no está configurado', mensaje)

    def test_obtener_xml_acepta_bom(self):
        self._cliente(xml=b'\xef\xbb\xbf' + XML)
        xml, error = obtener_xml(self.factura, self.configuracion)
        self.assertIsNone(error)
        self.assertTrue(xml.endswith(b'</rDE>'))


@override_settings(
    EMAIL_BACKEND='apps.factura.gmail_api_backend.GmailApiBackend',
    GMAIL_CLIENT_ID='id', GMAIL_CLIENT_SECRET='secreto', GMAIL_REFRESH_TOKEN='refresh',
)
class GmailApiBackendTest(TestCase):
    def test_pide_token_y_envia_mensaje_codificado(self):
        import base64
        import json

        from apps.factura import gmail_api_backend

        gmail_api_backend._token.update(valor=None, vence=0.0)
        llamadas = []

        def falso_llamar(url, data, headers):
            llamadas.append((url, data, headers))
            if url == gmail_api_backend.TOKEN_URL:
                return {'access_token': 'tok', 'expires_in': 3600}
            return {'id': 'abc'}

        with mock.patch.object(gmail_api_backend, '_llamar', side_effect=falso_llamar):
            correo = mail.EmailMessage('Asunto', 'Cuerpo', 'yo@gmail.com', ['cliente@correo.com'])
            correo.attach('KuDE.pdf', PDF, 'application/pdf')
            self.assertEqual(correo.send(), 1)

        self.assertEqual([url for url, _, _ in llamadas], [gmail_api_backend.TOKEN_URL, gmail_api_backend.SEND_URL])
        _, data, headers = llamadas[1]
        self.assertEqual(headers['Authorization'], 'Bearer tok')
        crudo = base64.urlsafe_b64decode(json.loads(data)['raw'])
        self.assertIn(b'To: cliente@correo.com', crudo)
        self.assertIn(b'KuDE.pdf', crudo)

    def test_error_de_api_se_informa(self):
        from apps.factura import gmail_api_backend

        gmail_api_backend._token.update(valor=None, vence=0.0)
        with mock.patch.object(gmail_api_backend, '_llamar', side_effect=gmail_api_backend.GmailApiError('401')):
            with self.assertRaises(gmail_api_backend.GmailApiError):
                mail.EmailMessage('A', 'B', 'yo@gmail.com', ['c@correo.com']).send()


class FacturaAgrupadaTest(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from apps.productos.models import Iva, Medida, Producto
        from apps.tipo_pago.models import TipoPago
        from apps.ventas.models import VentaDetalle, VentaTipoDePago

        ConfiguracionEmpresa.objects.create(
            nombre_empresa='Empresa', ruc='80000000-1', direccion='Asunción', nro_timbrado='12345678',
            vigencia_timbrado_desde=date(2026, 1, 1),
        )
        medida = Medida.objects.create(descripcion='Unidad', prefijo='UNI', codigo_set=77)
        iva = Iva.objects.create(descripcion='10')
        self.producto = Producto.objects.create(nombre='Helado', precio_actual=11_000, id_medida=medida, id_iva=iva)
        self.efectivo = TipoPago.objects.create(descripcion='Efectivo')
        self.cliente_venta = Cliente.objects.create(documento='111', nombre='Ocasional', apellido='', correo='', celular='')
        self.cliente_factura = Cliente.objects.create(
            documento='2222222', nombre='Ana', apellido='Gómez', correo='ana@correo.com', celular='',
        )
        self.ventas = []
        ahora = timezone.now()
        for monto in (11_000, 22_000, 33_000):
            venta = Venta.objects.create(
                total_iva_10=monto / 11, total_iva_5=0, total_venta=monto, usuario_creacion=1,
                id_cliente=self.cliente_venta, fecha_venta=ahora,
            )
            VentaDetalle.objects.create(
                id_venta=venta, id_producto=self.producto, cantidad_producto=monto / 11_000, total_detalle=monto,
            )
            VentaTipoDePago.objects.create(id_venta=venta, id_tipo_pago=self.efectivo, monto=monto)
            self.ventas.append(venta)

        usuario = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'clave')
        self.client.force_login(usuario)

    def _emitir(self, ventas, cliente=None):
        return self.client.post('/factura/emitir-agrupada/', {
            'ventas': [v.id_venta for v in ventas],
            'cliente': (cliente or self.cliente_factura).id_cliente,
            'tipo_factura': Factura.TIPO_CONTADO,
        })

    def test_una_factura_para_varias_ventas_con_cliente_elegido(self):
        from apps.factura.facturasend_payload import construir_documento

        respuesta = self._emitir(self.ventas[:2])

        factura = Factura.objects.get()
        self.assertRedirects(respuesta, f'/factura/detalle/{factura.id_factura}/', fetch_redirect_response=False)
        self.assertEqual(factura.id_venta, self.ventas[0])
        self.assertEqual(factura.cliente, self.cliente_factura)
        self.assertEqual(factura.total, 33_000)
        self.assertEqual(factura.forma_pago, 'Efectivo: 33000')

        documento = construir_documento(factura)
        self.assertEqual(documento['cliente']['documentoNumero'], '2222222')
        self.assertEqual(len(documento['items']), 2)
        self.assertEqual(documento['condicion']['entregas'], [{'tipo': 1, 'monto': 33_000, 'moneda': 'PYG'}])

        detalle = self.client.get(f'/factura/detalle/{factura.id_factura}/')
        self.assertContains(detalle, 'Ana Gómez')
        self.assertEqual(detalle.context['factura'].total, 33_000)

    def test_ventas_agrupadas_quedan_facturadas_y_bloqueadas(self):
        self._emitir(self.ventas[:2])
        factura = Factura.objects.get()

        # No se pueden volver a facturar, ni solas ni en otro grupo.
        self._emitir(self.ventas[1:])
        self.assertEqual(Factura.objects.count(), 1)
        self.client.post(f'/factura/emitir/{self.ventas[1].id_venta}/', {'tipo_factura': Factura.TIPO_CONTADO})
        self.assertEqual(Factura.objects.count(), 1)

        # La grilla las muestra facturadas y no permite editarlas.
        grilla = self.client.get('/ventas/')
        self.assertContains(grilla, f'/factura/detalle/{factura.id_factura}/', count=4)
        respuesta = self.client.get(f'/ventas/editar_venta/{self.ventas[1].id_venta}')
        self.assertRedirects(respuesta, '/ventas/', fetch_redirect_response=False)

        # Anular desde cualquiera de las ventas anula la factura completa.
        self.client.post(f'/factura/anular/{self.ventas[1].id_venta}/')
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.ESTADO_ANULADA)

    def test_pendientes_del_dia_omite_las_facturadas(self):
        from django.utils import timezone

        self.client.post(f'/factura/emitir/{self.ventas[0].id_venta}/', {'tipo_factura': Factura.TIPO_CONTADO})
        respuesta = self.client.get(f'/factura/emitir-agrupada/?fecha={timezone.localdate():%Y-%m-%d}')

        self.assertEqual(list(respuesta.context['ventas']), self.ventas[1:])
        self.assertEqual(respuesta.context['total'], 55_000)
        self.assertEqual(respuesta.context['cliente_sugerido'], self.cliente_venta.id_cliente)

    def test_sin_cliente_no_emite(self):
        respuesta = self.client.post('/factura/emitir-agrupada/', {'ventas': [self.ventas[0].id_venta]})
        self.assertEqual(Factura.objects.count(), 0)
        self.assertEqual(respuesta.status_code, 302)

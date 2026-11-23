import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.productos.models import Iva, Medida, Producto
from apps.tipo_pago.models import TipoPago
from apps.ventas.models import TipoVenta, Venta, VentaDetalle, VentaTipoDePago


class FormularioVentaTest(TestCase):
    def setUp(self):
        medida = Medida.objects.create(descripcion='Unidad', prefijo='UNI')
        iva = Iva.objects.create(descripcion='10')
        self.helado = Producto.objects.create(
            nombre='Helado', precio_actual=11_000, precio_pedidos_ya=None, id_medida=medida, id_iva=iva,
        )
        self.cono = Producto.objects.create(
            nombre='Cono', precio_actual=5_500, precio_pedidos_ya=0, id_medida=medida, id_iva=iva,
        )
        # Los ids 1, 2 y 3 son efectivo, POS y transferencia.
        for descripcion in ('Efectivo', 'POS', 'Transferencia'):
            TipoPago.objects.create(descripcion=descripcion)
        self.salon = TipoVenta.objects.create(nombre='Salón')
        self.cliente = Cliente.objects.create(documento='111', nombre='Ana', apellido='Gómez', correo='', celular='')
        self.sin_nombre = Cliente.objects.create(
            documento='0', nombre='Sin', apellido='Nombre', correo='', celular='',
            tipo_documento=Cliente.TIPO_DOC_INNOMINADO,
        )
        usuario = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'clave')
        self.client.force_login(usuario)

    def _datos_venta(self, **extra):
        datos = {
            'tipo_venta': self.salon.id,
            'cliente': self.cliente.id_cliente,
            'total_venta': '16500', 'total_iva_10': '1500', 'total_iva_5': '0',
            'efectivo': '16500', 'pos': '0', 'transferencia': '0',
            'fecha_venta': '',
            'productos_json': json.dumps([
                {'id_producto': self.helado.id_producto, 'cantidad': 1, 'total_detalle': '11000',
                 'total_detalle_iva_10': '1000', 'total_detalle_iva_5': '0'},
                {'id_producto': self.cono.id_producto, 'cantidad': 1, 'total_detalle': '5500',
                 'total_detalle_iva_10': '500', 'total_detalle_iva_5': '0'},
            ]),
        }
        datos.update(extra)
        return datos

    def test_formulario_preselecciona_cliente_innominado_y_lista_productos(self):
        respuesta = self.client.get(reverse('ventas:crear_venta'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['cliente_seleccionado'], self.sin_nombre.id_cliente)
        productos = {p['id']: p for p in respuesta.context['productos_pos']}
        self.assertEqual(productos[self.helado.id_producto]['precio_py'], 11_000)  # sin precio PY usa el normal
        self.assertEqual(productos[self.cono.id_producto]['precio_py'], 0)        # 0 = no disponible en PY
        self.assertContains(respuesta, 'id="pos-productos"')

    def test_crear_venta_guarda_detalles_y_pagos(self):
        respuesta = self.client.post(reverse('ventas:crear_venta'), self._datos_venta(pos='6500', efectivo='10000'))
        self.assertRedirects(respuesta, reverse('ventas:ventas'), fetch_redirect_response=False)
        venta = Venta.objects.get()
        self.assertEqual(venta.total_venta, 16500)
        self.assertEqual(VentaDetalle.objects.filter(id_venta=venta).count(), 2)
        pagos = dict(VentaTipoDePago.objects.filter(id_venta=venta).values_list('id_tipo_pago_id', 'monto'))
        self.assertEqual(pagos, {1: 10000, 2: 6500})

    def test_seguir_vendiendo_vuelve_al_formulario(self):
        respuesta = self.client.post(reverse('ventas:crear_venta'), self._datos_venta(seguir_vendiendo='1'))
        self.assertRedirects(respuesta, reverse('ventas:crear_venta'), fetch_redirect_response=False)

    def test_detalle_invalido_no_deja_venta_a_medias(self):
        datos = self._datos_venta(productos_json=json.dumps([
            {'id_producto': 9999, 'cantidad': 1, 'total_detalle': '1',
             'total_detalle_iva_10': '0', 'total_detalle_iva_5': '0'},
        ]))
        self.client.post(reverse('ventas:crear_venta'), datos)
        self.assertFalse(Venta.objects.exists())

    def test_editar_carga_carrito_y_pagos(self):
        self.client.post(reverse('ventas:crear_venta'), self._datos_venta(pos='6500', efectivo='10000'))
        venta = Venta.objects.get()
        respuesta = self.client.get(reverse('ventas:editar_venta', args=[venta.id_venta]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.context['carrito_inicial'],
            [{'id': self.helado.id_producto, 'cantidad': 1.0}, {'id': self.cono.id_producto, 'cantidad': 1.0}],
        )
        self.assertEqual(respuesta.context['pagos_iniciales'], {'efectivo': 10000, 'pos': 6500, 'transferencia': 0})
        self.assertEqual(respuesta.context['cliente_seleccionado'], self.cliente.id_cliente)

    def test_editar_reemplaza_detalles_y_pagos(self):
        self.client.post(reverse('ventas:crear_venta'), self._datos_venta())
        venta = Venta.objects.get()
        datos = self._datos_venta(
            total_venta='11000', total_iva_10='1000', efectivo='0', transferencia='11000',
            productos_json=json.dumps([
                {'id_producto': self.helado.id_producto, 'cantidad': 1, 'total_detalle': '11000',
                 'total_detalle_iva_10': '1000', 'total_detalle_iva_5': '0'},
            ]),
        )
        self.client.post(reverse('ventas:editar_venta', args=[venta.id_venta]), datos)
        venta.refresh_from_db()
        self.assertEqual(venta.total_venta, 11000)
        self.assertEqual(VentaDetalle.objects.filter(id_venta=venta).count(), 1)
        pagos = list(VentaTipoDePago.objects.filter(id_venta=venta).values_list('id_tipo_pago_id', 'monto'))
        self.assertEqual(pagos, [(3, 11000)])

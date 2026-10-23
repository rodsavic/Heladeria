from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.clientes.models import Cliente
from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.facturasend_payload import construir_documento
from apps.factura.models import Factura
from apps.productos.models import Iva, Medida, Producto
from apps.tipo_pago.models import TipoPago

from .models import ConceptoContrato, Contrato
from .services import FacturacionError, contratos_del_periodo, facturar_contrato


class DatosContratoMixin:
    def setUp(self):
        medida = Medida.objects.create(descripcion="Unidad", prefijo="UNI", codigo_set=77)
        iva = Iva.objects.create(descripcion="10")
        producto = Producto.objects.create(
            nombre="Servicio de alquiler", precio_actual=0, id_medida=medida, id_iva=iva
        )
        self.configuracion = ConfiguracionEmpresa.objects.create(
            nombre_empresa="Empresa", ruc="80000000-1", direccion="Asunción", nro_timbrado="12345678",
            vigencia_timbrado_desde=date(2026, 1, 1), vigencia_timbrado_hasta=date(2026, 12, 31),
            producto_alquiler=producto,
        )
        self.cliente = Cliente.objects.create(
            documento="1234567", nombre="Juan", apellido="Pérez", correo="", celular="",
        )
        self.tipo_pago = TipoPago.objects.create(descripcion="Transferencia")
        self.contrato = Contrato.objects.create(
            id_cliente=self.cliente,
            descripcion="Local 3",
            observacion="Garantía: pagaré por Gs. 5.000.000 ({periodo})",
            fecha_inicio=date(2026, 3, 15),
        )
        ConceptoContrato.objects.create(
            id_contrato=self.contrato, descripcion="Alquiler Local 3 - {periodo}",
            observacion="Texto largo " * 60, monto=3_300_000, iva=10,
        )
        ConceptoContrato.objects.create(
            id_contrato=self.contrato, descripcion="Alquiler vivienda", monto=2_100_000, iva=5,
        )
        ConceptoContrato.objects.create(
            id_contrato=self.contrato, tipo=ConceptoContrato.TIPO_GARANTIA,
            descripcion="Depósito en garantía", monto=1_000_000, iva=0, cobro_unico=True,
        )


class FacturacionAlquileresTest(DatosContratoMixin, TestCase):
    def test_factura_con_iva_5_y_10_descripcion_larga_y_garantia(self):
        factura = facturar_contrato(self.contrato, date(2026, 10, 1), self.configuracion, 1, self.tipo_pago)

        venta = factura.id_venta
        self.assertEqual(venta.total_venta, 6_400_000)
        self.assertEqual(venta.total_iva_10, 300_000)
        self.assertEqual(venta.total_iva_5, 100_000)
        self.assertEqual(factura.tipo_transaccion, Factura.TRANSACCION_SERVICIOS)

        documento = construir_documento(factura)
        self.assertEqual(documento["tipoTransaccion"], 2)
        self.assertIn("Octubre 2026", documento["observacion"])
        items = documento["items"]
        self.assertEqual([i["iva"] for i in items], [10, 5, 0])
        self.assertEqual(items[0]["descripcion"], "Alquiler Local 3 - Octubre 2026")
        self.assertTrue(items[0]["observacion"].startswith("Texto largo"))
        self.assertEqual(items[2]["ivaTipo"], 3)

    def test_no_factura_dos_veces_y_garantia_solo_la_primera(self):
        facturar_contrato(self.contrato, date(2026, 10, 1), self.configuracion, 1, self.tipo_pago)
        with self.assertRaises(FacturacionError):
            facturar_contrato(self.contrato, date(2026, 10, 1), self.configuracion, 1, self.tipo_pago)

        factura = facturar_contrato(
            self.contrato, date(2026, 11, 1), self.configuracion, 1, self.tipo_pago, montos={
                self.contrato.conceptos.first().id_concepto: 3_520_000,
            }
        )
        self.assertEqual(factura.id_venta.total_venta, 3_520_000 + 2_100_000)

    def test_factura_anulada_libera_el_periodo(self):
        factura = facturar_contrato(self.contrato, date(2026, 10, 1), self.configuracion, 1, self.tipo_pago)
        factura.estado = Factura.ESTADO_ANULADA
        factura.save()
        nueva = facturar_contrato(self.contrato, date(2026, 10, 1), self.configuracion, 1, self.tipo_pago)
        self.assertNotEqual(nueva.nro_factura, factura.nro_factura)

    def test_contrato_anual_se_factura_en_el_mes_de_inicio(self):
        self.contrato.periodicidad = Contrato.PERIODICIDAD_ANUAL
        self.contrato.save()
        self.assertEqual(contratos_del_periodo(2026, 10), [])
        [(contrato, periodo, facturado)] = contratos_del_periodo(2027, 3)
        self.assertEqual(contrato.etiqueta_periodo(periodo), "Marzo 2027 a Febrero 2028")
        self.assertIsNone(facturado)

    def test_contrato_fuera_de_vigencia(self):
        self.contrato.fecha_fin = date(2026, 9, 30)
        self.contrato.save()
        self.assertEqual(contratos_del_periodo(2026, 10), [])
        self.assertEqual(len(contratos_del_periodo(2026, 2)), 0)
        self.assertEqual(len(contratos_del_periodo(2026, 3)), 1)


class PantallasAlquileresTest(DatosContratoMixin, TestCase):
    def setUp(self):
        super().setUp()
        usuario = get_user_model().objects.create_superuser("admin", "admin@example.com", "clave")
        self.client.force_login(usuario)

    def test_listado_y_formularios(self):
        self.assertContains(self.client.get("/alquileres/"), "Local 3")
        self.assertEqual(self.client.get("/alquileres/crear/").status_code, 200)
        respuesta = self.client.get(f"/alquileres/editar/{self.contrato.id_contrato}/")
        self.assertContains(respuesta, "Alquiler Local 3 - {periodo}")

    def test_facturar_periodo_desde_la_pantalla(self):
        respuesta = self.client.get("/alquileres/facturar/?anio=2026&mes=10")
        self.assertContains(respuesta, "Alquiler Local 3 - Octubre 2026")

        respuesta = self.client.post(
            "/alquileres/facturar/?anio=2026&mes=10",
            {
                "contratos": [self.contrato.id_contrato],
                f"tipo_pago_{self.contrato.id_contrato}": self.tipo_pago.id_tipo_pago,
            },
            follow=True,
        )
        self.assertContains(respuesta, "Facturado")
        self.assertEqual(Factura.objects.count(), 1)
        factura = Factura.objects.get()
        self.assertEqual(factura.id_venta.total_venta, 6_400_000)
        self.assertEqual(factura.forma_pago, "Transferencia: 6400000")

    def test_facturar_exige_forma_de_pago(self):
        respuesta = self.client.post(
            "/alquileres/facturar/?anio=2026&mes=10",
            {"contratos": [self.contrato.id_contrato]},
            follow=True,
        )
        self.assertContains(respuesta, "selecciona la forma de pago")
        self.assertEqual(Factura.objects.count(), 0)

    def test_editar_contrato_conserva_y_modifica_conceptos(self):
        url = f"/alquileres/editar/{self.contrato.id_contrato}/"
        # El formulario debe incluir la clave oculta de cada concepto existente.
        respuesta = self.client.get(url)
        for concepto in self.contrato.conceptos.all():
            self.assertContains(respuesta, f'value="{concepto.id_concepto}"')

        conceptos = list(self.contrato.conceptos.all())
        datos = {
            "id_cliente": self.cliente.id_cliente,
            "descripcion": "Local 3 renovado",
            "periodicidad": Contrato.PERIODICIDAD_MENSUAL,
            "fecha_inicio": "2026-03-15",
            "fecha_fin": "",
            "observacion": "",
            "activo": "on",
            "conceptos-TOTAL_FORMS": "4",
            "conceptos-INITIAL_FORMS": "3",
            "conceptos-MIN_NUM_FORMS": "1",
            "conceptos-MAX_NUM_FORMS": "1000",
        }
        for i, concepto in enumerate(conceptos):
            datos.update({
                f"conceptos-{i}-id_concepto": concepto.id_concepto,
                f"conceptos-{i}-tipo": concepto.tipo,
                f"conceptos-{i}-descripcion": concepto.descripcion,
                f"conceptos-{i}-observacion": concepto.observacion,
                f"conceptos-{i}-monto": concepto.monto,
                f"conceptos-{i}-iva": concepto.iva,
            })
        datos["conceptos-0-monto"] = 3_520_000
        datos["conceptos-2-DELETE"] = "on"
        datos.update({
            "conceptos-3-tipo": ConceptoContrato.TIPO_OTRO,
            "conceptos-3-descripcion": "Expensas",
            "conceptos-3-monto": 200_000,
            "conceptos-3-iva": 10,
        })

        respuesta = self.client.post(url, datos)
        self.assertRedirects(respuesta, "/alquileres/")
        self.contrato.refresh_from_db()
        self.assertEqual(self.contrato.descripcion, "Local 3 renovado")
        self.assertEqual(
            [(c.descripcion, c.monto) for c in self.contrato.conceptos.all()],
            [("Alquiler Local 3 - {periodo}", 3_520_000), ("Alquiler vivienda", 2_100_000), ("Expensas", 200_000)],
        )

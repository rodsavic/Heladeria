from django.urls import path

from apps.factura.views import (
    actualizarEstadoFacturaView,
    anularFacturaView,
    detalleFacturaView,
    emitirFacturaView,
    kudeFacturaView,
    reenviarEmailFacturaView,
    reenviarFacturaView,
)

app_name = 'factura'

urlpatterns = [
    path('emitir/<int:id_venta>/', emitirFacturaView, name='emitir_factura'),
    path('anular/<int:id_venta>/', anularFacturaView, name='anular_factura'),
    path('detalle/<int:id_factura>/', detalleFacturaView, name='detalle_factura'),
    path('estado/<int:id_factura>/', actualizarEstadoFacturaView, name='actualizar_estado_factura'),
    path('reenviar/<int:id_factura>/', reenviarFacturaView, name='reenviar_factura'),
    path('kude/<int:id_factura>/', kudeFacturaView, name='kude_factura'),
    path('email/<int:id_factura>/', reenviarEmailFacturaView, name='reenviar_email_factura'),
]

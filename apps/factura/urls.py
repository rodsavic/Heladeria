from django.urls import path

from apps.factura.views import emitirFacturaView, anularFacturaView, detalleFacturaView

app_name = 'factura'

urlpatterns = [
    path('emitir/<int:id_venta>/', emitirFacturaView, name='emitir_factura'),
    path('anular/<int:id_venta>/', anularFacturaView, name='anular_factura'),
    path('detalle/<int:id_factura>/', detalleFacturaView, name='detalle_factura'),
]

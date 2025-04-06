from django.urls import path
from apps.ventas.views import *

app_name = 'ventas'

urlpatterns = [
    path('', ventasReadView, name='ventas'),
    path('ventas/<str:fecha>', ventasReadView, name='ventas'),
    path('crear_venta/', ventasCreateView, name='crear_venta'),
    path('editar_venta/<str:id_venta>',ventasEditView, name='editar_venta'),
    path('eliminar_venta/<str:id_venta>',ventasDeleteView, name='eliminar_venta'),
    path('detalle_venta/<str:id_venta>', ventaDetalleView, name='detalle_venta'),
    path('ventas_historial/',historialDeVentasView,name='ventas_historial')
]

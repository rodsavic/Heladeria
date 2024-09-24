from django.urls import path
from apps.ventas.views import *

app_name = 'ventas'

urlpatterns = [
    path('', ventasReadView, name='ventas'),
    path('crear_venta/', ventasCreateView, name='crear_venta'),
    path('eliminar_venta/<str:id_venta>',ventasDeleteView, name='eliminar_venta')
]

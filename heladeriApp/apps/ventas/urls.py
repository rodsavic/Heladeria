from django.urls import path
from apps.ventas.views import *

app_name = 'ventas'

urlpatterns = [
    path('', ventasReadView, name='ventas'),
    path('crear_venta/', ventasCreateView, name='crear_venta')
]

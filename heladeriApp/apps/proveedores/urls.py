from django.urls import path
from apps.proveedores.views import *

app_name = 'proveedores'

urlpatterns = [
    path('', proveedorReadView, name='proveedores'),
    path('crear_proveedor/', createProveedorView, name='crear_proveedor'),
    path('eliminar_proveedor/<str:id_proveedor>',proveedorDeleteView, name='eliminar_proveedor'),
    path('editar_proveedor/<str:id_proveedor>',proveedorUpdateView, name='editar_proveedor'),
]
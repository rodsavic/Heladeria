from django.urls import path
from .views import *

app_name = 'proveedores'

urlpatterns = [
    path('', proveedorReadView, name='proveedores'),
    path('crear_proveedor/', createProveedorView, name='crear_proveedor')
]
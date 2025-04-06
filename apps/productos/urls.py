from django.urls import path
from apps.productos.views import *

app_name = 'productos'

urlpatterns = [
    path('',productosReadView, name='productos'),
    path('crear_producto/', createProductosView, name='crear_producto'),
    path('eliminar_producto/<str:id_producto>',productoDeleteView, name='eliminar_producto'),
    path('editar_producto/<str:id_producto>',ProductoUpdateView, name='editar_producto'),
]

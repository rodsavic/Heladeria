from django.urls import path
from apps.clientes.views import *

app_name = 'clientes'
urlpatterns = [
    path('', clienteReadView, name='clientes'),
    path('crear_cliente/', crearCliente, name='crear_cliente'),
    path('eliminar_cliente/<str:id_cliente>',clienteDeleteView, name='eliminar_cliente'),
    path('editar_cliente/<str:id_cliente>',clienteUpdateView, name='editar_cliente'),
]

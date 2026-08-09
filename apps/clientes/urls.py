from django.urls import path
from apps.clientes.views import *

app_name = 'clientes'
urlpatterns = [
    path('', clienteReadView, name='clientes'),
    path('crear_cliente/', crearCliente, name='crear_cliente'),
    path('crear_cliente_ajax/', crearClienteAjax, name='crear_cliente_ajax'),
    path('eliminar_cliente/<str:id_cliente>',clienteDeleteView, name='eliminar_cliente'),
    path('editar_cliente/<str:id_cliente>',clienteUpdateView, name='editar_cliente'),
    path('clientes_json/', clientesJson, name='clientes_json'),
]

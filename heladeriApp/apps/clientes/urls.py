from django.urls import path
from . import views

app_name = 'clientes'
urlpatterns = [
    path('', views.clienteReadView, name='clientes'),
    path('crear_cliente/', views.crearCliente, name='crear_cliente')
]

from django.urls import path

from apps.inventario.views import (
    inventarioReadView,
    inventarioCreateView,
    inventarioUpdateView,
    inventarioDeleteView,
    produccionCreateView,
    produccionListView,
    produccionCambiarEstadoView,
)

app_name = 'inventario'
urlpatterns = [
    path('',inventarioReadView, name='inventario'),
    path('crear', inventarioCreateView, name='crear_inventario'),
    path('editar/<int:id>/', inventarioUpdateView, name='editar_inventario'),
    path('eliminar/<int:id>', inventarioDeleteView, name='eliminar_inventario'),
    path('produccion/', produccionListView, name='lista_produccion'),
    path('produccion/crear/', produccionCreateView, name='crear_produccion'),
    path('produccion/<int:id>/estado/', produccionCambiarEstadoView, name='cambiar_estado_produccion'),
]

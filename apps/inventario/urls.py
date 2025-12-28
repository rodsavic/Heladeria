from django.urls import path

from apps.inventario.views import inventarioReadView, inventarioCreateView, inventarioUpdateView, inventarioDeleteView

app_name = 'inventario'
urlpatterns = [
    path('',inventarioReadView, name='inventario'),
    path('crear', inventarioCreateView, name='crear_inventario'),
    path('editar/<int:id>/', inventarioUpdateView, name='editar_inventario'),
    path('eliminar/<int:id>', inventarioDeleteView, name='eliminar_inventario'),
]
from django.urls import path
from . import views


app_name = "usuarios"

urlpatterns = [
    path("",views.usuariosReadView, name="usuarios"),
    path("crear-usuario/", views.createUserView, name="usuarios_create"),
    path("modificar-usuario/<int:id>", views.usuarioUpdateView, name="usuarios_modificar"),
    path("cambiar-estado/<int:id>/", views.usuarioCambiarEstadoView, name="usuarios_cambiar_estado"),
    path("roles/", views.rolReadView, name="roles"),
    path("crear_rol/", views.crearRol, name="crear_rol"),
    path('roles/editar/<int:id>/', views.editarRolView, name='editar_rol'),
]

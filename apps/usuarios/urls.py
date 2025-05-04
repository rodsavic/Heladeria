from django.urls import path
from . import views


app_name = "usuarios"

urlpatterns = [
    path("",views.usuariosReadView, name="usuarios"),
    path("crear-usuario/", views.createUserView, name="usuarios_create"),
    path("modificar-usuario/<str:id>", views.usuarioUpdateView, name="usuarios_modificar"),
    path("roles/", views.rolReadView, name="roles"),
    path("crear_rol/", views.crearRol, name="crear_rol"),
    path("permisos/", views.permisoReadView, name="permisos"),
    path("crear_permiso/", views.crearPermiso, name="crear_permiso")
]

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/', include("apps.home.urls")),
    path('', include("apps.authentication.urls")),
    path("usuarios/", include("apps.usuarios.urls")),
    path("clientes/", include("apps.clientes.urls")),
    path("productos/", include("apps.productos.urls")),
    path("proveedores/", include("apps.proveedores.urls")),
    path("ventas/", include("apps.ventas.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("inventario/", include("apps.inventario.urls")),
]


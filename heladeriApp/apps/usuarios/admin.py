from django.contrib import admin

from apps.usuarios.models import *

# Register your models here.
admin.site.register(Usuario)
admin.site.register(Rol)
admin.site.register(Permiso)
admin.site.register(RolPermiso)
admin.site.register(UsuarioRol)

from django.contrib import admin
from django.contrib.auth.models import Permission

from apps.usuarios.models import *

# Register your models here.
admin.site.register(Usuario)
admin.site.register(User)
admin.site.register(Permission)
admin.site.register(Rol)
admin.site.register(Permiso)
admin.site.register(RolPermiso)
admin.site.register(UsuarioRol)

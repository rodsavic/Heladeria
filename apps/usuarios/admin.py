from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission

from apps.usuarios.models import *


@admin.register(User)
class UsuarioAdmin(UserAdmin):
    # UserAdmin maneja la contrasena con hash; un ModelAdmin comun la guardaria en texto plano.
    fieldsets = UserAdmin.fieldsets + (
        ('Datos adicionales', {'fields': ('telefono', 'direccion', 'fecha_nacimiento', 'cargo')}),
    )


admin.site.register(Usuario)
admin.site.register(Permission)
admin.site.register(Rol)
admin.site.register(Permiso)
admin.site.register(RolPermiso)
admin.site.register(UsuarioRol)

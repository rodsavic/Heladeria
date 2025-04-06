from django.contrib.auth.hashers import make_password
from django.db import models


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False)
    apellido = models.CharField(max_length=100, null=False)
    documento = models.CharField(max_length=20, null=False)
    nombre_usuario = models.CharField(max_length=15, null=False)
    usuario_creacion = models.IntegerField(null=True)
    usuario_modificacion = models.IntegerField(null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(null=True)
    contrasena = models.CharField(max_length=255, null=False)

    def set_password(self, raw_password):
        self.contrasena = make_password(raw_password)

    class Meta:
        managed = False
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombre_usuario}"

    '''
    def get_absolute_url(self):
        return reverse("_detail", kwargs={"pk": self.pk})
    '''


class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100, null= False)

    class Meta:
        managed = False
        db_table = 'roles'
        # Para la vista en el admin
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return f"{self.descripcion}"


class Permiso(models.Model):
    id_permiso = models.AutoField(primary_key=True)
    descripcion = models.CharField(max_length=100, null=False)

    class Meta:
        managed = False
        db_table = 'permisos'
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'

    def __str__(self):
        return f"{self.descripcion}"


class UsuarioRol(models.Model):
    id = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario', null=False)
    id_rol = models.ForeignKey(Rol, on_delete=models.CASCADE, db_column='id_rol', null=False)

    class Meta:
        managed = False
        db_table = 'usuario_rol'
        unique_together = (('id_rol', 'id_usuario'),)
        verbose_name = 'UsuarioRol'
        verbose_name_plural = 'UsuariosRoles'

    def __str__(self):
        return f"idUsuario: {self.id_usuario}, idRol: {self.id_rol}"


class RolPermiso(models.Model):
    id = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Rol, on_delete=models.CASCADE, db_column='id_rol', null=False)
    id_permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE, db_column='id_permiso', null=False)

    class Meta:
        managed = False
        db_table = 'rol_permiso'
        unique_together = (('id_rol', 'id_permiso'),)
        verbose_name = 'RolPermiso'
        verbose_name_plural = 'RolesPermisos'

    def __str__(self):
        return f"idPermiso: {self.id_permiso}, idRol: {self.id_rol}"
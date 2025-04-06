from django.db import models

class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    documento = models.CharField(max_length=50, db_column='documento',null=False)
    nombre = models.CharField(max_length=100, db_column='nombre', null=False)
    telefono = models.CharField(max_length=100, db_column='telefono', null=False)
    direccion = models.CharField(max_length=100, db_column='direccion', null=False)
    correo = models.CharField(max_length=255, db_column='correo', null=False)
    usuario_creacion = models.IntegerField(db_column='usuario_creacion', null=False)
    usuario_modificacion = models.IntegerField(db_column='usuario_modificacion', null=False)
    fecha_creacion = models.DateTimeField(db_column='fecha_creacion', auto_now_add=True)
    fecha_modificacion = models.DateTimeField(db_column='fecha_modificacion', null=True)
    estado =  models.CharField(max_length=15, db_column='estado', null=False, default='activo')
    
    class Meta:
        managed = False
        db_table = 'proveedores'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return f'id_proveedor: {self.id_proveedor}, proveedor: {self.nombre}'

from django.db import models

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    documento = models.CharField(max_length=16, db_column= 'documento',null=False)
    nombre = models.CharField(max_length=100, db_column= 'nombre',null=False)
    apellido = models.CharField(max_length=100, db_column= 'apellido',null=False)
    correo = models.CharField(max_length=100, db_column= 'correo',null=False)
    celular = models.CharField(max_length=50, db_column= 'celular',null=False)
    direccion = models.CharField(max_length=255,db_column= 'direccion', null=True)
    estado = models.CharField(max_length=16, db_column= 'estado', null=True)

    class Meta:
        managed = False
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f'IdCliente: {self.id_cliente} , Cliente {self.nombre}'
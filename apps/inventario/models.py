from django.db import models

class Inventario(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False, blank=False)
    tipo = models.CharField(max_length=1, null=False, blank=False)
    cantidad = models.IntegerField(null=False, blank=False)

    def __str__(self):
        return f'{self.nombre} - {self.tipo} - {self.cantidad}'

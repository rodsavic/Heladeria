from django.db import models

class Inventario(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False, blank=False)
    cant_chico = models.IntegerField(default=0,null=False, blank=False)
    cant_grande = models.IntegerField(default=0,null=False, blank=False)

    def __str__(self):
        return f'{self.nombre} - {self.cant_chico} - {self.cant_grande}'

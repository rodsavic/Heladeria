from django.db import models


class Inventario(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, null=False, blank=False)
    cant_chico = models.IntegerField(default=0, null=False, blank=False)
    cant_grande = models.IntegerField(default=0, null=False, blank=False)

    def __str__(self):
        return f'{self.nombre} - {self.cant_chico} - {self.cant_grande}'


class ProduccionDiaria(models.Model):
    fecha = models.DateField(unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'Produccion {self.fecha}'


class ProduccionDetalle(models.Model):
    produccion = models.ForeignKey(
        ProduccionDiaria,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    fabricar_chico = models.IntegerField(default=0)
    fabricar_grande = models.IntegerField(default=0)

    class Meta:
        unique_together = ('produccion', 'inventario')
        ordering = ['inventario__nombre']

    def __str__(self):
        return f'{self.inventario.nombre}: C{self.fabricar_chico} G{self.fabricar_grande}'

from django.db import models


class EnvioFormulario(models.Model):
    """Token de un formulario ya procesado. El indice unico hace que, si el
    mismo formulario llega dos veces (doble click, boton atras y reenvio),
    solo el primero se procese."""
    token = models.CharField(max_length=64, unique=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'envios_formulario'
        verbose_name = 'Envío de formulario'
        verbose_name_plural = 'Envíos de formulario'

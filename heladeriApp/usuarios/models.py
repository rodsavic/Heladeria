from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# Create your models here.
class Usuario(models.Model):
    nombre = models.CharField(max_length=100, null=False)
    apellido = models.CharField(max_length=100,null=False)
    nombre_usuario = models.CharField(max_length=15,null=False)
    usuario_creacion = models.IntegerField
    usuario_modificacion = models.IntegerField
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField

    class Meta:
        verbose_name = _("Usuario")
        verbose_name_plural = _("Usuarios")

    def __str__(self):
       return f"{self.nombre_usuario}"

    def get_absolute_url(self):
        return reverse("_detail", kwargs={"pk": self.pk})

from django.contrib import admin
from apps.ventas.models import *
# Register your models here.
admin.site.register(Venta)
admin.site.register(VentaDetalle)
admin.site.register(VentaTipoDePago)
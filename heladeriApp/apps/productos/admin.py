from django.contrib import admin
from apps.productos.models import *

admin.site.register(Producto)
admin.site.register(Categoria)
admin.site.register(CategoriaProducto)
admin.site.register(Medida)
admin.site.register(Iva)


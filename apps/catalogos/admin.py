from django.contrib import admin

from .models import Ciudad, Departamento, Distrito, Moneda, Pais

admin.site.register(Pais)
admin.site.register(Moneda)
admin.site.register(Departamento)
admin.site.register(Distrito)
admin.site.register(Ciudad)

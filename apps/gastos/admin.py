from django.contrib import admin

from .models import Gasto


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("id_gasto", "descripcion", "costo", "fecha")
    search_fields = ("descripcion",)
    list_filter = ("fecha",)


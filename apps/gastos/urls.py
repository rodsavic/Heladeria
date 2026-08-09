from django.urls import path

from .views import gastoCreateView, gastoDeleteView, gastoUpdateView, gastosReadView

app_name = "gastos"

urlpatterns = [
    path("", gastosReadView, name="gastos"),
    path("crear/", gastoCreateView, name="crear_gasto"),
    path("editar/<int:id_gasto>/", gastoUpdateView, name="editar_gasto"),
    path("eliminar/<int:id_gasto>/", gastoDeleteView, name="eliminar_gasto"),
]


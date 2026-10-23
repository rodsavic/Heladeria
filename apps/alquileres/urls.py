from django.urls import path

from .views import contratoCreateView, contratosReadView, contratoUpdateView, facturarAlquileresView

app_name = "alquileres"

urlpatterns = [
    path("", contratosReadView, name="contratos"),
    path("crear/", contratoCreateView, name="crear_contrato"),
    path("editar/<int:id_contrato>/", contratoUpdateView, name="editar_contrato"),
    path("facturar/", facturarAlquileresView, name="facturar"),
]

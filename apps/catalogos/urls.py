from django.urls import path

from apps.catalogos.views import ciudadesJson, distritosJson

app_name = 'catalogos'

urlpatterns = [
    path('distritos/<int:id_departamento>/', distritosJson, name='distritos_json'),
    path('ciudades/<int:id_distrito>/', ciudadesJson, name='ciudades_json'),
]

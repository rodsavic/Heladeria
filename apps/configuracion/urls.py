from django.urls import path

from apps.configuracion.views import configuracionEmpresaView

app_name = 'configuracion'

urlpatterns = [
    path('empresa/', configuracionEmpresaView, name='empresa'),
]

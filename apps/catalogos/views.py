from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import Ciudad, Distrito


@login_required(login_url="/")
def distritosJson(request, id_departamento):
    distritos = Distrito.objects.filter(departamento_id=id_departamento).values('codigo', 'descripcion')
    return JsonResponse({'items': list(distritos)})


@login_required(login_url="/")
def ciudadesJson(request, id_distrito):
    ciudades = Ciudad.objects.filter(distrito_id=id_distrito).values('codigo', 'descripcion')
    return JsonResponse({'items': list(ciudades)})

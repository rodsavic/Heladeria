from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.configuracion.models import ConfiguracionEmpresa


@login_required(login_url='/')
def configuracionEmpresaView(request):
    if not request.user.is_superuser:
        messages.error(request, 'Solo el administrador puede editar la configuración de la empresa.')
        return redirect('dashboard:dashboard')

    configuracion, _ = ConfiguracionEmpresa.objects.get_or_create(
        id=1,
        defaults={
            'nombre_empresa': 'Mi Empresa',
            'ruc': '0000000-0',
            'direccion': 'Dirección',
            'nro_timbrado': '00000000',
            'vigencia_timbrado_desde': '2026-01-01',
            'vigencia_timbrado_hasta': '2026-12-31',
            'establecimiento': '001',
            'punto_expedicion': '001',
            'secuencia_actual': 1,
        }
    )

    if request.method == 'POST':
        configuracion.nombre_empresa = request.POST.get('nombre_empresa', '').strip()
        configuracion.ruc = request.POST.get('ruc', '').strip()
        configuracion.direccion = request.POST.get('direccion', '').strip()
        configuracion.nro_timbrado = request.POST.get('nro_timbrado', '').strip()
        configuracion.vigencia_timbrado_desde = request.POST.get('vigencia_timbrado_desde')
        configuracion.vigencia_timbrado_hasta = request.POST.get('vigencia_timbrado_hasta')
        configuracion.establecimiento = request.POST.get('establecimiento', '001').zfill(3)
        configuracion.punto_expedicion = request.POST.get('punto_expedicion', '001').zfill(3)
        secuencia_actual = request.POST.get('secuencia_actual', '1')
        configuracion.secuencia_actual = int(secuencia_actual) if secuencia_actual.isdigit() else 1
        configuracion.save()
        messages.success(request, 'Configuración de empresa actualizada correctamente.')
        return redirect('configuracion:empresa')

    context = {
        'configuracion': configuracion
    }
    return render(request, 'configuracion/empresa.html', context=context)

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.inventario.models import Inventario, ProduccionDiaria, ProduccionDetalle


# Create your views here.
@login_required(login_url='/')
def inventarioReadView(request):
    listaInventario = Inventario.objects.all().order_by('nombre')
    paginator = Paginator(listaInventario, 10)
    page = request.GET.get('page')
    items_page = paginator.get_page(page)
    context = {
        "items_page": items_page,
        "inventario": listaInventario,
    }
    return render(request, "inventario/inventario.html", context=context)

def inventarioCreateView(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        cant_chico = request.POST.get("cant_chico")
        cant_grande = request.POST.get("cant_grande")

        inventario_nuevo = Inventario(
            nombre=nombre,
            cant_chico=int(cant_chico),
            cant_grande=int(cant_grande)
        )

        inventario_nuevo.save()

        messages.success(request, "Inventario creado exitosamente")
        return redirect("inventario:inventario")
    else:
        return render(request, "inventario/inventario_create.html")


@login_required
@require_POST
def inventarioUpdateView(request, id):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        inventario = Inventario.objects.get(id=id)

        inventario.nombre = request.POST.get("nombre")
        inventario.cant_chico = int(request.POST.get("cant_chico"))
        inventario.cant_grande = int(request.POST.get("cant_grande"))
        inventario.save()

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})

@login_required(login_url="/")
def inventarioDeleteView(request, id):
    inventario = get_object_or_404(Inventario, pk=id)
    inventario.delete()
    messages.success(request, "Objeto eliminado correctamente")
    return redirect('inventario:inventario')


@login_required(login_url='/')
def produccionCreateView(request):
    inventario = Inventario.objects.all().order_by('nombre')

    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        inventario_ids = request.POST.getlist('inventario_id[]')
        fabricar_chicos = request.POST.getlist('fabricar_chico[]')
        fabricar_grandes = request.POST.getlist('fabricar_grande[]')

        nuevo_nombre = (request.POST.get('nuevo_nombre') or '').strip()
        nuevo_stock_chico = int(request.POST.get('nuevo_stock_chico') or 0)
        nuevo_stock_grande = int(request.POST.get('nuevo_stock_grande') or 0)
        nuevo_fabricar_chico = int(request.POST.get('nuevo_fabricar_chico') or 0)
        nuevo_fabricar_grande = int(request.POST.get('nuevo_fabricar_grande') or 0)

        if not fecha:
            messages.error(request, "Debes seleccionar una fecha de producción.")
            return redirect('inventario:crear_produccion')

        detalles_payload = []
        for idx, inventario_id in enumerate(inventario_ids):
            chico = int(fabricar_chicos[idx] or 0)
            grande = int(fabricar_grandes[idx] or 0)
            if chico <= 0 and grande <= 0:
                continue
            detalles_payload.append({
                'inventario_id': int(inventario_id),
                'fabricar_chico': chico,
                'fabricar_grande': grande,
            })

        if nuevo_nombre:
            inventario_nuevo, _ = Inventario.objects.get_or_create(
                nombre=nuevo_nombre,
                defaults={
                    'cant_chico': nuevo_stock_chico,
                    'cant_grande': nuevo_stock_grande,
                }
            )
            if nuevo_fabricar_chico > 0 or nuevo_fabricar_grande > 0:
                detalles_payload.append({
                    'inventario_id': inventario_nuevo.id,
                    'fabricar_chico': nuevo_fabricar_chico,
                    'fabricar_grande': nuevo_fabricar_grande,
                })

        if len(detalles_payload) == 0:
            messages.warning(request, "No se registraron cantidades a fabricar.")
            return redirect('inventario:crear_produccion')

        produccion = ProduccionDiaria.objects.create(fecha=fecha, estado=ProduccionDiaria.ESTADO_CREADO)

        for detalle in detalles_payload:
            ProduccionDetalle.objects.create(
                produccion=produccion,
                inventario_id=detalle['inventario_id'],
                fabricar_chico=detalle['fabricar_chico'],
                fabricar_grande=detalle['fabricar_grande']
            )

        messages.success(request, "Lista de producción guardada correctamente.")
        return redirect('inventario:lista_produccion')

    context = {
        'inventario': inventario,
        'hoy': date.today().isoformat(),
    }
    return render(request, 'inventario/produccion_create.html', context=context)


@login_required(login_url='/')
def produccionListView(request):
    producciones = ProduccionDiaria.objects.prefetch_related('detalles__inventario').all()
    paginator = Paginator(producciones, 10)
    page = request.GET.get('page')
    items_page = paginator.get_page(page)
    context = {
        'items_page': items_page
    }
    return render(request, 'inventario/produccion_lista.html', context=context)


@login_required(login_url='/')
@require_POST
def produccionCambiarEstadoView(request, id):
    produccion = get_object_or_404(ProduccionDiaria, id=id)
    nuevo_estado = request.POST.get('estado')
    estados_validos = {
        ProduccionDiaria.ESTADO_REALIZADO,
        ProduccionDiaria.ESTADO_CANCELADO,
        ProduccionDiaria.ESTADO_CREADO
    }

    if nuevo_estado not in estados_validos:
        messages.error(request, "Estado de producción no válido.")
        return redirect('inventario:lista_produccion')

    # Regla de irreversibilidad:
    # Si ya está REALIZADO no puede pasar a CANCELADO y viceversa.
    if produccion.estado in (ProduccionDiaria.ESTADO_REALIZADO, ProduccionDiaria.ESTADO_CANCELADO):
        if nuevo_estado != produccion.estado:
            messages.error(request, "No se puede cambiar el estado: la producción ya está cerrada.")
            return redirect('inventario:lista_produccion')

    # Aplicar al inventario solo la primera vez que pasa a REALIZADO.
    if nuevo_estado == ProduccionDiaria.ESTADO_REALIZADO and produccion.estado != ProduccionDiaria.ESTADO_REALIZADO:
        with transaction.atomic():
            detalles = ProduccionDetalle.objects.select_related('inventario').filter(produccion=produccion)
            for detalle in detalles:
                inventario_item = detalle.inventario
                inventario_item.cant_chico = int(inventario_item.cant_chico) + int(detalle.fabricar_chico)
                inventario_item.cant_grande = int(inventario_item.cant_grande) + int(detalle.fabricar_grande)
                inventario_item.save(update_fields=['cant_chico', 'cant_grande'])

    produccion.estado = nuevo_estado
    produccion.save()
    messages.success(request, f"Estado actualizado a {nuevo_estado}.")
    return redirect('inventario:lista_produccion')

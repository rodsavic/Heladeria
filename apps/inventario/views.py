from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
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

        produccion, _ = ProduccionDiaria.objects.get_or_create(fecha=fecha)
        ProduccionDetalle.objects.filter(produccion=produccion).delete()

        detalles_creados = 0
        for idx, inventario_id in enumerate(inventario_ids):
            chico = int(fabricar_chicos[idx] or 0)
            grande = int(fabricar_grandes[idx] or 0)
            if chico <= 0 and grande <= 0:
                continue

            ProduccionDetalle.objects.create(
                produccion=produccion,
                inventario_id=int(inventario_id),
                fabricar_chico=chico,
                fabricar_grande=grande
            )
            detalles_creados += 1

        if nuevo_nombre:
            inventario_nuevo, _ = Inventario.objects.get_or_create(
                nombre=nuevo_nombre,
                defaults={
                    'cant_chico': nuevo_stock_chico,
                    'cant_grande': nuevo_stock_grande,
                }
            )
            if nuevo_fabricar_chico > 0 or nuevo_fabricar_grande > 0:
                ProduccionDetalle.objects.update_or_create(
                    produccion=produccion,
                    inventario=inventario_nuevo,
                    defaults={
                        'fabricar_chico': nuevo_fabricar_chico,
                        'fabricar_grande': nuevo_fabricar_grande,
                    }
                )
                detalles_creados += 1

        if detalles_creados == 0:
            ProduccionDetalle.objects.filter(produccion=produccion).delete()
            messages.warning(request, "No se registraron cantidades a fabricar.")
            return redirect('inventario:crear_produccion')

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

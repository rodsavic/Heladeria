from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.inventario.models import Inventario


# Create your views here.
@login_required(login_url='/')
def inventarioReadView(request):
    listaInventario = Inventario.objects.all().order_by('nombre')
    columnas = ["Nombre", "Tipo","Cantidad"]
    paginator = Paginator(listaInventario, 10)
    page = request.GET.get('page')
    items_page = paginator.get_page(page)
    context = {
        "columnas": columnas,
        "items_page": items_page,
        "inventario": listaInventario,
    }
    return render(request, "inventario/inventario.html", context=context)

def inventarioCreateView(request):
    if(request.method == "POST"):
        nombre = request.POST.get("nombre")
        tipo = request.POST.get("tipo")
        cantidad = request.POST.get("cantidad")

        inventario_nuevo = Inventario(
            nombre = nombre,
            tipo = tipo,
            cantidad = int(cantidad)
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
        inventario.tipo = request.POST.get("tipo")
        inventario.cantidad = int(request.POST.get("cantidad"))
        inventario.save()

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})

@login_required(login_url="/")
def inventarioDeleteView(request, id):
    inventario = get_object_or_404(Inventario, pk=id)
    inventario.delete()
    messages.success(request,"Objeto eliminado correctamente")
    return redirect('inventario:inventario')

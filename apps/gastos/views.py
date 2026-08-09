from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import GastoForm
from .models import Gasto


def es_admin(user):
    return user.is_authenticated and user.groups.filter(name="ADMIN").exists()


def _parse_fecha(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@login_required(login_url="/")
@user_passes_test(es_admin, login_url="/")
def gastosReadView(request):
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    descripcion = request.GET.get("descripcion", "").strip()
    orden_monto = request.GET.get("orden_monto", "desc").strip().lower()

    gastos = Gasto.objects.select_related("id_tipo_pago").all()

    fecha_desde_dt = _parse_fecha(fecha_desde)
    fecha_hasta_dt = _parse_fecha(fecha_hasta)

    if fecha_desde and not fecha_desde_dt:
        messages.error(request, "La fecha desde no es valida.")
    if fecha_hasta and not fecha_hasta_dt:
        messages.error(request, "La fecha hasta no es valida.")
    if fecha_desde_dt:
        gastos = gastos.filter(fecha__gte=fecha_desde_dt)
    if fecha_hasta_dt:
        gastos = gastos.filter(fecha__lte=fecha_hasta_dt)
    if descripcion:
        gastos = gastos.filter(descripcion__icontains=descripcion)

    if orden_monto == "asc":
        gastos = gastos.order_by("costo", "-fecha", "-id_gasto")
    else:
        orden_monto = "desc"
        gastos = gastos.order_by("-costo", "-fecha", "-id_gasto")

    columnas = ["Descripcion", "Costo", "Fecha", "Forma de Pago"]
    paginator = Paginator(gastos, 10)
    page_number = request.GET.get("page")
    items_page = paginator.get_page(page_number)

    filtros = request.GET.copy()
    if "page" in filtros:
        filtros.pop("page")

    context = {
        "columnas": columnas,
        "items_page": items_page,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "descripcion": descripcion,
        "orden_monto": orden_monto,
        "querystring": filtros.urlencode(),
    }
    return render(request, "gastos/gastos.html", context=context)


@login_required(login_url="/")
@user_passes_test(es_admin, login_url="/")
def gastoCreateView(request):
    if request.method == "POST":
        form = GastoForm(request.POST)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.usuario_creacion = request.user.id
            gasto.save()
            messages.success(request, "Gasto creado exitosamente.")
            return redirect("gastos:gastos")
        messages.error(request, "Revisa los campos del formulario.")
    else:
        form = GastoForm(initial={"fecha": timezone.localdate()})

    return render(request, "gastos/crear_gasto.html", {"form": form})


@login_required(login_url="/")
@user_passes_test(es_admin, login_url="/")
def gastoUpdateView(request, id_gasto):
    gasto = get_object_or_404(Gasto, pk=id_gasto)

    if request.method == "POST":
        form = GastoForm(request.POST, instance=gasto)
        if not form.has_changed():
            messages.info(request, "No ha hecho ningun cambio.")
            return redirect("gastos:gastos")
        if form.is_valid():
            gasto_actualizado = form.save(commit=False)
            gasto_actualizado.usuario_modificacion = request.user.id
            gasto_actualizado.fecha_modificacion = timezone.now()
            gasto_actualizado.save()
            messages.success(request, "Gasto modificado exitosamente.")
            return redirect("gastos:gastos")
        messages.error(request, "Revisa los campos del formulario.")
    else:
        form = GastoForm(instance=gasto)

    return render(
        request,
        "gastos/editar_gasto.html",
        {"form": form, "gasto": gasto},
    )


@login_required(login_url="/")
@user_passes_test(es_admin, login_url="/")
def gastoDeleteView(request, id_gasto):
    gasto = get_object_or_404(Gasto, pk=id_gasto)
    if request.method == "POST":
        gasto.delete()
        messages.success(request, "Gasto eliminado correctamente.")
    return redirect("gastos:gastos")


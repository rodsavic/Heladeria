from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.emision import enviar_si_corresponde
from apps.factura.models import Factura
from apps.tipo_pago.models import TipoPago

from .forms import AYUDA_VARIABLES, ConceptoFormSet, ContratoForm
from .models import MESES, Contrato
from .services import (
    FacturacionError,
    conceptos_a_facturar,
    contratos_del_periodo,
    facturar_contrato,
)


@login_required(login_url="/")
@permission_required("alquileres.view_contrato", login_url="/")
def contratosReadView(request):
    buscar = request.GET.get("buscar", "").strip()
    estado = request.GET.get("estado", "activos")

    contratos = Contrato.objects.select_related("id_cliente").annotate(
        # Monto periodico: los conceptos de cobro unico (ej. deposito) no se repiten.
        total=Sum("conceptos__monto", filter=Q(conceptos__cobro_unico=False))
    )
    if buscar:
        contratos = contratos.filter(
            Q(descripcion__icontains=buscar)
            | Q(id_cliente__nombre__icontains=buscar)
            | Q(id_cliente__apellido__icontains=buscar)
            | Q(id_cliente__documento__icontains=buscar)
        )
    if estado == "activos":
        contratos = contratos.filter(activo=True)
    elif estado == "inactivos":
        contratos = contratos.filter(activo=False)
    contratos = contratos.order_by("id_cliente__nombre", "descripcion")

    paginator = Paginator(contratos, 10)
    items_page = paginator.get_page(request.GET.get("page"))

    filtros = request.GET.copy()
    if "page" in filtros:
        filtros.pop("page")

    context = {
        "columnas": ["Cliente", "Descripción", "Periodicidad", "Inicio", "Fin", "Monto por período", "Estado"],
        "items_page": items_page,
        "buscar": buscar,
        "estado": estado,
        "querystring": filtros.urlencode(),
    }
    return render(request, "alquileres/contratos.html", context=context)


def _guardar_contrato(request, contrato, template, mensaje_ok):
    form = ContratoForm(request.POST or None, instance=contrato)
    formset = ConceptoFormSet(request.POST or None, instance=contrato, prefix="conceptos")

    if request.method == "POST":
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                contrato = form.save(commit=False)
                if contrato.pk:
                    contrato.usuario_modificacion = request.user.id
                    contrato.fecha_modificacion = timezone.now()
                else:
                    contrato.usuario_creacion = request.user.id
                contrato.save()
                formset.instance = contrato
                formset.save()
            messages.success(request, mensaje_ok)
            return redirect("alquileres:contratos")
        messages.error(request, "Revisa los campos del formulario.")

    context = {
        "form": form,
        "formset": formset,
        "contrato": contrato,
        "ayuda_variables": AYUDA_VARIABLES,
    }
    return render(request, template, context=context)


@login_required(login_url="/")
@permission_required("alquileres.add_contrato", login_url="/")
def contratoCreateView(request):
    contrato = Contrato(fecha_inicio=timezone.localdate())
    return _guardar_contrato(request, contrato, "alquileres/crear_contrato.html", "Contrato creado exitosamente.")


@login_required(login_url="/")
@permission_required("alquileres.change_contrato", login_url="/")
def contratoUpdateView(request, id_contrato):
    contrato = get_object_or_404(Contrato, pk=id_contrato)
    return _guardar_contrato(request, contrato, "alquileres/editar_contrato.html", "Contrato modificado exitosamente.")


def _periodo_solicitado(request):
    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get("anio", hoy.year))
        mes = int(request.GET.get("mes", hoy.month))
    except ValueError:
        anio, mes = hoy.year, hoy.month
    if not 1 <= mes <= 12 or not 2000 <= anio <= 2100:
        anio, mes = hoy.year, hoy.month
    return anio, mes


@login_required(login_url="/")
@permission_required("alquileres.add_facturaalquiler", login_url="/")
def facturarAlquileresView(request):
    anio, mes = _periodo_solicitado(request)
    configuracion = ConfiguracionEmpresa.objects.first()
    if not configuracion:
        messages.error(request, "Debes configurar los datos de la empresa antes de emitir facturas.")
        return redirect("configuracion:empresa")

    tipos_pago = {str(tipo.id_tipo_pago): tipo for tipo in TipoPago.objects.order_by("descripcion")}

    if request.method == "POST":
        seleccionados = set(request.POST.getlist("contratos"))
        if not seleccionados:
            messages.warning(request, "No seleccionaste ningún contrato.")
        for contrato, periodo, facturado in contratos_del_periodo(anio, mes):
            if str(contrato.id_contrato) not in seleccionados or facturado:
                continue
            tipo_pago = tipos_pago.get(request.POST.get(f"tipo_pago_{contrato.id_contrato}", ""))
            if not tipo_pago:
                messages.error(request, f"{contrato.descripcion}: selecciona la forma de pago.")
                continue
            montos = {}
            for concepto in contrato.conceptos.all():
                valor = request.POST.get(f"monto_{concepto.id_concepto}", "").strip()
                if valor.isdigit():
                    montos[concepto.id_concepto] = int(valor)
            try:
                factura = facturar_contrato(contrato, periodo, configuracion, request.user.id, tipo_pago, montos)
            except FacturacionError as exc:
                messages.error(request, str(exc))
                continue
            ok, mensaje = enviar_si_corresponde(factura, configuracion)
            if ok:
                messages.success(request, f"{contrato.descripcion}: {mensaje}")
            else:
                messages.warning(request, f"{contrato.descripcion}: {mensaje}")
        return redirect(f"{request.path}?anio={anio}&mes={mes}")

    filas = []
    for contrato, periodo, facturado in contratos_del_periodo(anio, mes):
        conceptos = [] if facturado else conceptos_a_facturar(contrato)
        filas.append({
            "contrato": contrato,
            "periodo": contrato.etiqueta_periodo(periodo),
            "facturado": facturado,
            "factura": facturado.id_venta.factura_set.filter(estado=Factura.ESTADO_EMITIDA).first() if facturado else None,
            "conceptos": [
                {
                    "concepto": concepto,
                    "descripcion": contrato.completar_texto(concepto.descripcion, periodo),
                }
                for concepto in conceptos
            ],
            "total": sum(concepto.monto for concepto in conceptos),
        })

    context = {
        "anio": anio,
        "mes": mes,
        "meses": list(enumerate(MESES, start=1)),
        "filas": filas,
        "tipos_pago": tipos_pago.values(),
        "pendientes": sum(1 for fila in filas if not fila["facturado"]),
        "sin_producto": not configuracion.producto_alquiler_id,
    }
    return render(request, "alquileres/facturar.html", context=context)

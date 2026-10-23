from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.emision import crear_factura, enviar_si_corresponde
from apps.factura.facturasend_service import (
    ESTADOS_SIFEN_APROBADOS,
    ESTADOS_SIFEN_PENDIENTES,
    actualizar_estados,
    cancelar_documento,
    consultar_envios_email,
    enviar_documento,
    inutilizar_numero,
    obtener_kude,
    reenviar_email,
)
from apps.factura.models import Factura
from apps.ventas.models import Venta, VentaDetalle, VentaTipoDePago


@login_required(login_url='/')
def emitirFacturaView(request, id_venta):
    venta = get_object_or_404(Venta, id_venta=id_venta)
    factura_activa = Factura.objects.filter(id_venta=venta, estado=Factura.ESTADO_EMITIDA).first()
    if factura_activa:
        messages.warning(request, f'La venta ya tiene factura emitida: {factura_activa.nro_factura}')
        return redirect('ventas:ventas')

    configuracion = ConfiguracionEmpresa.objects.first()
    if not configuracion:
        messages.error(request, 'Debes configurar los datos de la empresa antes de emitir facturas.')
        return redirect('configuracion:empresa')

    if request.method == 'POST':
        tipo_factura = request.POST.get('tipo_factura', Factura.TIPO_CONTADO)
        factura = crear_factura(venta, tipo_factura=tipo_factura)
        ok, mensaje = enviar_si_corresponde(factura, configuracion)
        if ok:
            messages.success(request, mensaje)
        else:
            messages.warning(request, mensaje)

        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    context = {
        'venta': venta,
        'cliente': venta.id_cliente,
    }
    return render(request, 'factura/emitir_factura.html', context=context)


def _configuracion_facturasend():
    """Devuelve la ConfiguracionEmpresa si FacturaSend esta configurado, si no None."""
    configuracion = ConfiguracionEmpresa.objects.first()
    if configuracion and configuracion.facturasend_url and configuracion.facturasend_api_key:
        return configuracion
    return None


@login_required(login_url='/')
def anularFacturaView(request, id_venta):
    venta = get_object_or_404(Venta, id_venta=id_venta)
    factura = Factura.objects.filter(id_venta=venta, estado=Factura.ESTADO_EMITIDA).first()
    if not factura:
        messages.warning(request, 'No existe una factura emitida para anular en esta venta.')
        return redirect('ventas:ventas')

    configuracion = _configuracion_facturasend()
    mensaje_fs = ''
    error_fs = ''
    if configuracion:
        # Antes de decidir, se sincroniza el estado real en SIFEN.
        if factura.cdc and factura.estado_sifen in ESTADOS_SIFEN_PENDIENTES:
            actualizar_estados(configuracion, [factura])
            factura.refresh_from_db()

        motivo = 'Anulación solicitada por el emisor'
        if factura.estado_sifen in ESTADOS_SIFEN_PENDIENTES and factura.cdc:
            messages.warning(
                request,
                f'La factura {factura.nro_factura} todavía espera respuesta de SIFEN. '
                'Podrá anularla cuando sea aprobada o rechazada.'
            )
            return redirect('ventas:ventas')

        if factura.estado_sifen in ESTADOS_SIFEN_APROBADOS:
            # Aprobada: se cancela (maximo 48 hs). Si SIFEN no la cancela, la
            # factura sigue vigente fiscalmente y no se anula en el sistema.
            ok, mensaje_fs = cancelar_documento(factura, configuracion, motivo=motivo)
            if not ok:
                messages.error(request, f'No se pudo anular la factura {factura.nro_factura}: {mensaje_fs}')
                return redirect('ventas:ventas')
        else:
            # Nunca aprobada (no enviada o rechazada): el numero queda sin uso
            # en el timbrado y se debe inutilizar.
            ok, mensaje_fs = inutilizar_numero(factura, configuracion, motivo=motivo)
            if not ok:
                error_fs, mensaje_fs = mensaje_fs, ''

    factura.estado = Factura.ESTADO_ANULADA
    factura.fecha_anulacion = timezone.now()
    factura.save()

    if error_fs:
        messages.warning(
            request,
            f'Factura {factura.nro_factura} anulada localmente, pero no se pudo inutilizar el número '
            f'en SIFEN: {error_fs}'
        )
    elif mensaje_fs:
        messages.success(request, f'Factura {factura.nro_factura} anulada correctamente. {mensaje_fs}')
    else:
        messages.success(request, f'Factura {factura.nro_factura} anulada correctamente.')

    return redirect('ventas:ventas')


@login_required(login_url='/')
def actualizarEstadoFacturaView(request, id_factura):
    factura = get_object_or_404(Factura, id_factura=id_factura)
    configuracion = _configuracion_facturasend()
    if not configuracion or not factura.cdc:
        messages.warning(request, 'La factura no fue enviada a FacturaSend.')
        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    _, error = actualizar_estados(configuracion, [factura])
    if error:
        messages.error(request, f'No se pudo consultar el estado en FacturaSend: {error}')
    else:
        factura.refresh_from_db()
        messages.success(request, f'Estado SIFEN: {factura.get_estado_sifen_display()}.')
    return redirect('factura:detalle_factura', id_factura=factura.id_factura)


@login_required(login_url='/')
def reenviarFacturaView(request, id_factura):
    """Reenvia una factura no enviada o rechazada (con el mismo CDC si ya tenia)."""
    factura = get_object_or_404(Factura, id_factura=id_factura, estado=Factura.ESTADO_EMITIDA)
    configuracion = _configuracion_facturasend()
    reenviable = not factura.cdc or factura.estado_sifen == Factura.ESTADO_SIFEN_RECHAZADO
    if request.method != 'POST' or not configuracion or not reenviable:
        messages.warning(request, 'La factura no se puede reenviar a FacturaSend en su estado actual.')
        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    ok, mensaje_fs = enviar_documento(factura, configuracion)
    if ok:
        messages.success(request, mensaje_fs)
    else:
        messages.error(request, f'No se pudo reenviar a FacturaSend: {mensaje_fs}')
    return redirect('factura:detalle_factura', id_factura=factura.id_factura)


@login_required(login_url='/')
def reenviarEmailFacturaView(request, id_factura):
    """Reenvia por correo el KuDE de una factura aprobada. Si se indica una
    direccion en el formulario, se envia solo a esa."""
    factura = get_object_or_404(Factura, id_factura=id_factura)
    configuracion = _configuracion_facturasend()
    if request.method != 'POST' or not configuracion:
        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    email = request.POST.get('email', '').strip() or None
    ok, mensaje_fs = reenviar_email(factura, configuracion, email)
    if ok:
        messages.success(request, mensaje_fs)
    else:
        messages.error(request, f'No se pudo reenviar el correo: {mensaje_fs}')
    return redirect(f"{reverse('factura:detalle_factura', args=[factura.id_factura])}?correos=1")


@login_required(login_url='/')
def kudeFacturaView(request, id_factura):
    factura = get_object_or_404(Factura, id_factura=id_factura)
    configuracion = _configuracion_facturasend()
    if not configuracion:
        messages.warning(request, 'FacturaSend no está configurado.')
        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    pdf, error = obtener_kude(factura, configuracion)
    if error:
        messages.error(request, f'No se pudo obtener el KuDE: {error}')
        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="KuDE-{factura.nro_factura}.pdf"'
    return response


@login_required(login_url='/')
def detalleFacturaView(request, id_factura):
    factura = get_object_or_404(Factura, id_factura=id_factura)
    venta = factura.id_venta
    detalle_venta = VentaDetalle.objects.filter(id_venta=venta).select_related('id_producto')
    pagos = VentaTipoDePago.objects.filter(id_venta=venta).select_related('id_tipo_pago')
    configuracion = _configuracion_facturasend()

    # El historial de correos se consulta a FacturaSend solo cuando se pide
    # (?correos=1), para no demorar la apertura de cada factura.
    sifen_aprobado = factura.estado_sifen in ESTADOS_SIFEN_APROBADOS
    ver_correos = bool(configuracion and sifen_aprobado and request.GET.get('correos'))
    envios_email, error_envios = [], None
    if ver_correos:
        envios_email, error_envios = consultar_envios_email(factura, configuracion)

    context = {
        'factura': factura,
        'venta': venta,
        'cliente': venta.id_cliente,
        'detalles': detalle_venta,
        'pagos': pagos,
        'facturasend_activo': configuracion is not None,
        'sifen_pendiente': factura.estado_sifen in ESTADOS_SIFEN_PENDIENTES,
        'sifen_aprobado': sifen_aprobado,
        'ver_correos': ver_correos,
        'envios_email': envios_email,
        'error_envios': error_envios,
        'sifen_reenviable': factura.estado == Factura.ESTADO_EMITIDA and (
            not factura.cdc or factura.estado_sifen == Factura.ESTADO_SIFEN_RECHAZADO
        ),
    }
    return render(request, 'factura/detalle_factura.html', context=context)

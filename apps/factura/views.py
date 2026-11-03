from datetime import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.clientes.models import Cliente
from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.correo_respaldo import enviar_factura_gmail, gmail_configurado
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
from apps.factura.models import Factura, facturas_de_ventas
from apps.ventas.models import Venta, VentaDetalle, VentaTipoDePago


@login_required(login_url='/')
def emitirFacturaView(request, id_venta):
    venta = get_object_or_404(Venta, id_venta=id_venta)
    factura_activa = Factura.objects.de_venta(venta).filter(estado=Factura.ESTADO_EMITIDA).first()
    if factura_activa:
        messages.warning(request, f'La venta ya tiene factura emitida: {factura_activa.nro_factura}')
        return redirect('ventas:ventas')

    configuracion = ConfiguracionEmpresa.objects.first()
    if not configuracion:
        messages.error(request, 'Debes configurar los datos de la empresa antes de emitir facturas.')
        return redirect('configuracion:empresa')

    if request.method == 'POST':
        tipo_factura = request.POST.get('tipo_factura', Factura.TIPO_CONTADO)
        with transaction.atomic():
            # Bloquea la venta y repite el chequeo: dos POST simultaneos (doble click,
            # dos pestañas) pasarian ambos el control de arriba y emitirian dos facturas.
            Venta.objects.select_for_update().get(pk=venta.pk)
            factura_activa = Factura.objects.de_venta(venta).filter(estado=Factura.ESTADO_EMITIDA).first()
            if factura_activa:
                messages.warning(request, f'La venta ya tiene factura emitida: {factura_activa.nro_factura}')
                return redirect('factura:detalle_factura', id_factura=factura_activa.id_factura)
            factura = crear_factura(venta, tipo_factura=tipo_factura)
        # El envio a FacturaSend queda fuera de la transaccion para no retener el bloqueo durante la llamada HTTP.
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


def _ids_ventas(valores):
    """Convierte la lista de ids recibida (puede venir repetida si la grilla
    tiene checkboxes en la vista de escritorio y en la movil) en enteros unicos."""
    ids = set()
    for valor in valores:
        try:
            ids.add(int(valor))
        except (TypeError, ValueError):
            continue
    return sorted(ids)


@login_required(login_url='/')
def emitirFacturaAgrupadaView(request):
    """Emite una sola factura para varias ventas sin factura, con el cliente
    receptor que se elija.

    Las ventas llegan como `?ventas=1&ventas=2` (seleccionadas en la grilla) o
    con `?fecha=AAAA-MM-DD` para tomar todas las ventas de ese dia que todavia
    no tienen factura emitida.
    """
    configuracion = ConfiguracionEmpresa.objects.first()
    if not configuracion:
        messages.error(request, 'Debes configurar los datos de la empresa antes de emitir facturas.')
        return redirect('configuracion:empresa')

    if request.method == 'POST':
        ids = _ids_ventas(request.POST.getlist('ventas'))
        cliente = Cliente.objects.filter(id_cliente=request.POST.get('cliente') or None).first()
        tipo_factura = request.POST.get('tipo_factura', Factura.TIPO_CONTADO)
        if not ids:
            messages.warning(request, 'Seleccione al menos una venta para facturar.')
            return redirect('ventas:ventas')
        if not cliente:
            messages.warning(request, 'Seleccione el cliente de la factura.')
            consulta = urlencode([('ventas', i) for i in ids])
            return redirect(f"{reverse('factura:emitir_factura_agrupada')}?{consulta}")

        with transaction.atomic():
            # Se bloquean las ventas (en orden, para evitar deadlocks) y se
            # repite el chequeo: un doble envio no debe emitir dos facturas.
            ventas = list(Venta.objects.select_for_update().filter(pk__in=ids).order_by('pk'))
            facturadas = facturas_de_ventas(ids, [Factura.ESTADO_EMITIDA])
            if facturadas:
                nros = ', '.join(sorted({f.nro_factura for f in facturadas.values()}))
                messages.warning(request, f'Algunas ventas ya tienen factura emitida ({nros}); revise la selección.')
                return redirect('ventas:ventas')
            if len(ventas) != len(ids):
                messages.warning(request, 'Algunas ventas seleccionadas ya no existen; revise la selección.')
                return redirect('ventas:ventas')
            factura = crear_factura(ventas[0], tipo_factura=tipo_factura, ventas=ventas, cliente=cliente)

        # El envio a FacturaSend queda fuera de la transaccion para no retener el bloqueo durante la llamada HTTP.
        ok, mensaje = enviar_si_corresponde(factura, configuracion)
        if ok:
            messages.success(request, mensaje)
        else:
            messages.warning(request, mensaje)
        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    fecha = request.GET.get('fecha')
    if fecha:
        try:
            dia = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            messages.warning(request, 'Fecha inválida.')
            return redirect('ventas:ventas')
        candidatas = Venta.objects.filter(fecha_venta__date=dia)
    else:
        candidatas = Venta.objects.filter(pk__in=_ids_ventas(request.GET.getlist('ventas')))
    candidatas = list(candidatas.select_related('id_cliente', 'id_tipo_venta').order_by('fecha_venta', 'id_venta'))

    facturadas = facturas_de_ventas([v.id_venta for v in candidatas], [Factura.ESTADO_EMITIDA])
    ventas = [v for v in candidatas if v.id_venta not in facturadas]
    if not ventas:
        messages.warning(request, 'No hay ventas sin factura para facturar.')
        return redirect('ventas:ventas', fecha=fecha) if fecha else redirect('ventas:ventas')
    if len(ventas) < len(candidatas):
        messages.info(request, f'Se omitieron {len(candidatas) - len(ventas)} ventas que ya tienen factura emitida.')

    # Si todas las ventas son del mismo cliente se propone ese cliente.
    clientes_ventas = {v.id_cliente_id for v in ventas}
    context = {
        'ventas': ventas,
        'total': sum(v.total_venta for v in ventas),
        'clientes': Cliente.objects.order_by('nombre', 'apellido'),
        'cliente_sugerido': clientes_ventas.pop() if len(clientes_ventas) == 1 else None,
        'fecha': fecha,
    }
    return render(request, 'factura/emitir_factura_agrupada.html', context=context)


def _configuracion_facturasend():
    """Devuelve la ConfiguracionEmpresa si FacturaSend esta configurado, si no None."""
    configuracion = ConfiguracionEmpresa.objects.first()
    if configuracion and configuracion.facturasend_url and configuracion.facturasend_api_key:
        return configuracion
    return None


@login_required(login_url='/')
@permission_required("factura.change_factura", login_url="/")
@require_POST
def anularFacturaView(request, id_venta):
    venta = get_object_or_404(Venta, id_venta=id_venta)
    factura = Factura.objects.de_venta(venta).filter(estado=Factura.ESTADO_EMITIDA).first()
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
@require_POST
def enviarEmailGmailFacturaView(request, id_factura):
    """Respaldo del correo de FacturaSend: envia el KuDE y el XML desde la
    cuenta de Gmail propia. Si se indica una direccion, se envia solo a esa."""
    factura = get_object_or_404(Factura, id_factura=id_factura)
    configuracion = _configuracion_facturasend()
    if not configuracion:
        messages.warning(request, 'FacturaSend no está configurado.')
        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    email = request.POST.get('email', '').strip() or None
    ok, mensaje = enviar_factura_gmail(factura, configuracion, email)
    if ok:
        messages.success(request, mensaje)
    else:
        messages.error(request, f'No se pudo enviar el correo por Gmail: {mensaje}')
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
    ventas = factura.get_ventas()
    detalle_venta = (
        VentaDetalle.objects.filter(id_venta__in=ventas)
        .select_related('id_producto')
        .order_by('id_venta__fecha_venta', 'id_venta', 'pk')
    )
    pagos = VentaTipoDePago.objects.filter(id_venta__in=ventas).select_related('id_tipo_pago')
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
        'cliente': factura.cliente,
        'detalles': detalle_venta,
        'pagos': pagos,
        'facturasend_activo': configuracion is not None,
        'sifen_pendiente': factura.estado_sifen in ESTADOS_SIFEN_PENDIENTES,
        'sifen_aprobado': sifen_aprobado,
        'ver_correos': ver_correos,
        'envios_email': envios_email,
        'error_envios': error_envios,
        'gmail_activo': gmail_configurado(),
        'sifen_reenviable': factura.estado == Factura.ESTADO_EMITIDA and (
            not factura.cdc or factura.estado_sifen == Factura.ESTADO_SIFEN_RECHAZADO
        ),
    }
    return render(request, 'factura/detalle_factura.html', context=context)

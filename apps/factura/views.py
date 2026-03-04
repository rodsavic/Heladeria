from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.configuracion.models import ConfiguracionEmpresa
from apps.factura.models import Factura
from apps.ventas.models import Venta, VentaDetalle, VentaTipoDePago


def _obtener_forma_pago_texto(venta):
    pagos = VentaTipoDePago.objects.filter(id_venta=venta).select_related('id_tipo_pago')
    if not pagos:
        return 'Sin forma de pago'

    partes = []
    for pago in pagos:
        partes.append(f"{pago.id_tipo_pago.descripcion}: {int(pago.monto)}")
    return ", ".join(partes)


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
        id_tipo = 1 if tipo_factura == Factura.TIPO_CONTADO else 2
        forma_pago = _obtener_forma_pago_texto(venta)
        nro_factura = configuracion.generar_nro_factura()

        factura = Factura.objects.create(
            nro_factura=nro_factura,
            id_venta=venta,
            id_tipo=id_tipo,
            tipo_factura=tipo_factura,
            forma_pago=forma_pago,
            estado=Factura.ESTADO_EMITIDA,
            nombre_empresa=configuracion.nombre_empresa,
            ruc_empresa=configuracion.ruc,
            direccion_empresa=configuracion.direccion,
            nro_timbrado=configuracion.nro_timbrado,
            vigencia_timbrado_desde=configuracion.vigencia_timbrado_desde,
            vigencia_timbrado_hasta=configuracion.vigencia_timbrado_hasta,
        )

        configuracion.secuencia_actual += 1
        configuracion.save()

        messages.success(request, f'Factura {factura.nro_factura} emitida correctamente.')
        return redirect('factura:detalle_factura', id_factura=factura.id_factura)

    context = {
        'venta': venta,
        'cliente': venta.id_cliente,
    }
    return render(request, 'factura/emitir_factura.html', context=context)


@login_required(login_url='/')
def anularFacturaView(request, id_venta):
    venta = get_object_or_404(Venta, id_venta=id_venta)
    factura = Factura.objects.filter(id_venta=venta, estado=Factura.ESTADO_EMITIDA).first()
    if not factura:
        messages.warning(request, 'No existe una factura emitida para anular en esta venta.')
        return redirect('ventas:ventas')

    factura.estado = Factura.ESTADO_ANULADA
    factura.fecha_anulacion = timezone.now()
    factura.save()
    messages.success(request, f'Factura {factura.nro_factura} anulada correctamente.')
    return redirect('ventas:ventas')


@login_required(login_url='/')
def detalleFacturaView(request, id_factura):
    factura = get_object_or_404(Factura, id_factura=id_factura)
    venta = factura.id_venta
    detalle_venta = VentaDetalle.objects.filter(id_venta=venta).select_related('id_producto')
    pagos = VentaTipoDePago.objects.filter(id_venta=venta).select_related('id_tipo_pago')
    context = {
        'factura': factura,
        'venta': venta,
        'cliente': venta.id_cliente,
        'detalles': detalle_venta,
        'pagos': pagos,
    }
    return render(request, 'factura/detalle_factura.html', context=context)

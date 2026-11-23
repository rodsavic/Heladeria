import json
import logging
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from apps.clientes.forms import ClienteForm
from apps.envio_unico import envio_unico
from apps.clientes.models import Cliente
from apps.factura.models import Factura, facturas_de_ventas
from apps.productos.models import CategoriaProducto, Producto
from apps.tipo_pago.models import TipoPago
from apps.ventas.forms import *
from apps.ventas.models import VentaTipoDePago, TipoVenta


def _cliente_form_modal():
    # El modal de alta rapida vive dentro del <form> de la venta: sin atributo
    # required (bloquearia el submit de la venta) y con ids cliente_* que usa ventas.js.
    return ClienteForm(auto_id='cliente_%s', use_required_attribute=False)


def _parsear_fecha_venta(valor, por_defecto):
    """Convierte el valor del input datetime-local (hora local de Asuncion, sin
    zona) en un datetime con zona. Acepta el valor con o sin segundos."""
    if not valor:
        return por_defecto
    fecha = parse_datetime(valor)
    if fecha is None:
        raise ValueError(f'Fecha de venta inválida: {valor}')
    if timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha)
    return fecha


ESTADOS_FACTURA_BLOQUEANTES = (Factura.ESTADO_EMITIDA, Factura.ESTADO_ANULADA)
MENSAJE_VENTA_BLOQUEADA = 'La venta tiene una factura emitida o anulada y no se puede {accion}.'


def _venta_tiene_factura(id_venta):
    # Una venta facturada (aunque la factura este anulada) ya fue informada
    # a SIFEN: modificarla o borrarla dejaria la factura sin respaldo.
    return Factura.objects.de_venta(id_venta).filter(estado__in=ESTADOS_FACTURA_BLOQUEANTES).exists()


# Ventana usada para ordenar la grilla de productos por los mas vendidos.
DIAS_POPULARIDAD = 60


def _productos_para_venta():
    """Productos para la grilla del punto de venta, los mas vendidos primero."""
    desde = timezone.now() - timedelta(days=DIAS_POPULARIDAD)
    productos = (
        Producto.objects.select_related('id_iva')
        .annotate(veces_vendido=Count(
            'ventadetalle', filter=Q(ventadetalle__id_venta__fecha_venta__gte=desde)
        ))
        .order_by('-veces_vendido', 'nombre')
    )

    categorias_por_producto = {}
    categorias = {}
    for cp in CategoriaProducto.objects.select_related('id_categoria'):
        categorias_por_producto.setdefault(cp.id_producto_id, []).append(cp.id_categoria_id)
        categorias[cp.id_categoria_id] = cp.id_categoria.descripcion

    datos = []
    for producto in productos:
        precio = float(producto.precio_actual or 0)
        # Sin precio PedidosYa (None) se usa el normal; con 0 el producto no se ofrece en PedidosYa.
        precio_py = precio if producto.precio_pedidos_ya is None else float(producto.precio_pedidos_ya)
        try:
            iva = int(producto.id_iva.descripcion)
        except (TypeError, ValueError):
            iva = 0
        datos.append({
            'id': producto.id_producto,
            'nombre': producto.nombre,
            'precio': precio,
            'precio_py': precio_py,
            'iva': iva,
            'categorias': categorias_por_producto.get(producto.id_producto, []),
        })

    categorias_lista = [
        {'id': id_cat, 'nombre': nombre}
        for id_cat, nombre in sorted(categorias.items(), key=lambda c: c[1].lower())
    ]
    return datos, categorias_lista


def _cliente_por_defecto():
    """Cliente innominado ("Sin nombre") que se preselecciona en las ventas nuevas."""
    return (
        Cliente.objects.filter(tipo_documento=Cliente.TIPO_DOC_INNOMINADO)
        .order_by('id_cliente')
        .first()
    )


def _contexto_formulario_venta(venta=None):
    productos, categorias = _productos_para_venta()
    if venta:
        cliente_seleccionado = venta.id_cliente_id
    else:
        cliente_defecto = _cliente_por_defecto()
        cliente_seleccionado = cliente_defecto.id_cliente if cliente_defecto else None
    return {
        'productos_pos': productos,
        'categorias_pos': categorias,
        'clientes': Cliente.objects.all().order_by('nombre'),
        'tipo_venta': TipoVenta.objects.all().order_by('id'),
        'cliente_seleccionado': cliente_seleccionado,
        'cliente_form': _cliente_form_modal(),
        'now': timezone.now(),
    }


def _guardar_detalles_y_pagos(venta, productos_json, pago_efectivo, pago_pos, pago_transferencia):
    if not productos_json:
        raise ValueError("No se recibieron los detalles de la venta.")
    productos_data = json.loads(productos_json)
    if not productos_data:
        raise ValueError("La venta no tiene productos.")

    for detalle in productos_data:
        VentaDetalle.objects.create(
            id_venta=venta,
            id_producto=Producto.objects.get(id_producto=detalle['id_producto']),
            cantidad_producto=detalle['cantidad'],
            total_detalle=detalle['total_detalle'],
            total_iva_5=detalle['total_detalle_iva_5'],
            total_iva_10=detalle['total_detalle_iva_10'],
        )

    for id_tipo_pago, monto in ((1, pago_efectivo), (2, pago_pos), (3, pago_transferencia)):
        if monto > 0:
            VentaTipoDePago.objects.create(
                id_venta=venta,
                id_tipo_pago=TipoPago.objects.get(id_tipo_pago=id_tipo_pago),
                monto=monto,
            )


@login_required(login_url="/")
def ventasReadView(request, fecha=None):
    if fecha:
        fecha_venta = datetime.strptime(fecha, '%Y-%m-%d').date()
    else:
        fecha_venta = timezone.localdate()

    ventas = Venta.objects.filter(fecha_venta__date=fecha_venta).order_by('-fecha_venta')
    # Obtener los id_venta de las ventas filtradas
    ids_ventas = ventas.values_list('id_venta', flat=True)

    # Traer todos los pagos de las ventas filtradas
    pagos = VentaTipoDePago.objects.filter(id_venta__in=ids_ventas).select_related('id_tipo_pago')

    # Diccionario { id_venta: ["Efectivo", "Tarjeta"] }
    formas_pago_dict = {}
    for p in pagos:
        formas_pago_dict.setdefault(p.id_venta_id, []).append(p.id_tipo_pago.descripcion)

    total_efectivo_salon = 0

    # Incluye las ventas que forman parte de una factura agrupada.
    factura_por_venta = facturas_de_ventas(ids_ventas, [Factura.ESTADO_EMITIDA])
    ventas_con_factura = set(facturas_de_ventas(ids_ventas, ESTADOS_FACTURA_BLOQUEANTES))
    ventas_agrupadas = set(
        Factura.ventas.through.objects.filter(
            venta_id__in=ids_ventas, factura__estado=Factura.ESTADO_EMITIDA
        ).values_list('venta_id', flat=True)
    )

    # Agregar atributo dinámico a cada venta
    for venta in ventas:
        venta.formas_pago = ", ".join(formas_pago_dict.get(venta.id_venta, []))
        factura = factura_por_venta.get(venta.id_venta)
        venta.factura_emitida = factura is not None
        venta.id_factura_emitida = factura.id_factura if factura else None
        venta.nro_factura_emitida = factura.nro_factura if factura else ''
        venta.factura_agrupada = venta.id_venta in ventas_agrupadas
        venta.bloqueada = venta.id_venta in ventas_con_factura

    # Filtrar los pagos con id_tipo_pago=1 y los id_venta obtenidos
    pagos_efectivo = VentaTipoDePago.objects.filter(id_tipo_pago=1, id_venta__in=ids_ventas)

    # Obtener solo los montos (opcional)
    montos_efectivo = pagos_efectivo.values_list('monto', flat=True)

    # Si necesitas sumarlos
    total_monto_efectivo = pagos_efectivo.aggregate(total=Sum('monto'))['total']
    total_ventas = ventas.aggregate(total_ventas=Sum('total_venta'))['total_ventas'] or 0
    # Total de ventas de tipo 1 (Salón) y en efectivo
    total_ventas_salon_efectivo = VentaTipoDePago.objects.filter(
        id_venta__id_tipo_venta=1,
        id_tipo_pago=1,
        id_venta__in = ids_ventas
    ).aggregate(total=Sum('monto'))['total'] or 0

    total_ventas_salon = VentaTipoDePago.objects.filter(
        id_venta__id_tipo_venta=1,
        id_venta__in=ids_ventas
    ).aggregate(total=Sum('monto'))['total'] or 0

    columnas = ['Cliente', 'Total', 'IVA 10','Forma de Pago','Tipo de Venta', 'Fecha']
    paginator = Paginator(ventas, 10)
    page_number = request.GET.get('page', 1)
    ventas_por_pagina = paginator.get_page(page_number)

    context = {
        'columnas': columnas,
        'ventas_por_pagina': ventas_por_pagina,
        'total_ventas': total_ventas,
        'total_ventas_salon': total_ventas_salon,
        'total_ventas_salon_efectivo': total_ventas_salon_efectivo,
        'fecha_venta': fecha_venta,
        'hay_ventas_sin_factura': len(factura_por_venta) < len(ids_ventas),
    }

    return render(request, 'ventas/ventas.html', context=context)


@login_required(login_url="/")
@envio_unico('ventas:ventas')
def ventasCreateView(request):
    if request.method == 'POST':
        try:
            pago_pos = float(request.POST.get('pos', 0) or 0)
            pago_efectivo = float(request.POST.get('efectivo', 0) or 0)
            pago_transferencia = float(request.POST.get('transferencia', 0) or 0)
            id_tipo_venta = request.POST.get('tipo_venta')
            if not id_tipo_venta:
                raise ValueError("Debes seleccionar un tipo de venta.")

            # Si el usuario no toca nada, queda la actual
            fecha_venta = _parsear_fecha_venta(request.POST.get('fecha_venta'), por_defecto=timezone.now())

            # Todo o nada: una falla en un detalle no deja la venta a medias.
            with transaction.atomic():
                nueva_venta = Venta.objects.create(
                    fecha_venta=fecha_venta,
                    total_iva_10=request.POST['total_iva_10'],
                    total_iva_5=request.POST['total_iva_5'],
                    id_cliente=Cliente.objects.get(id_cliente=request.POST['cliente']),
                    total_venta=request.POST['total_venta'],
                    usuario_creacion=request.user.id,
                    id_tipo_venta=TipoVenta.objects.get(id=id_tipo_venta),
                )
                _guardar_detalles_y_pagos(
                    nueva_venta, request.POST.get('productos_json'),
                    pago_efectivo, pago_pos, pago_transferencia,
                )

            messages.success(request, f"Venta #{nueva_venta.id_venta} registrada exitosamente")
            # "Seguir vendiendo": vuelve directo a un formulario vacio.
            if request.POST.get('seguir_vendiendo') == '1':
                return redirect('ventas:crear_venta')
            return redirect('ventas:ventas')
        except Exception as e:
            error_message = str(e)
            messages.error(request, f"Error al registrar venta {error_message}")
            logging.error(f'Error al crear venta: {error_message}')
            return redirect('ventas:crear_venta')

    return render(request, 'ventas/crear_venta.html', context=_contexto_formulario_venta())


@login_required(login_url="/")
@permission_required("ventas.change_venta", login_url="/")
def ventasEditView(request, id_venta):
    if _venta_tiene_factura(id_venta):
        messages.warning(request, MENSAJE_VENTA_BLOQUEADA.format(accion='editar'))
        return redirect('ventas:ventas')

    # Las ventas generadas desde un contrato de alquiler tienen lineas con
    # descripcion propia que este formulario no conserva.
    if VentaDetalle.objects.filter(id_venta=id_venta).exclude(descripcion='').exists():
        messages.warning(request, 'Esta venta proviene de un contrato de alquiler y no se puede editar desde aquí.')
        return redirect('ventas:ventas')

    if request.method == 'POST':
        try:
            pago_pos = float(request.POST.get('pos', 0) or 0)
            pago_efectivo = float(request.POST.get('efectivo', 0) or 0)
            pago_transferencia = float(request.POST.get('transferencia', 0) or 0)
            id_tipo_venta = request.POST.get('tipo_venta')
            if not id_tipo_venta:
                raise ValueError("Debes seleccionar un tipo de venta.")
            venta = get_object_or_404(Venta, id_venta=id_venta)

            # Si el campo llega vacio se conserva la fecha original de la venta.
            fecha_venta = _parsear_fecha_venta(request.POST.get('fecha_venta'), por_defecto=venta.fecha_venta)

            with transaction.atomic():
                venta.total_iva_10 = request.POST['total_iva_10']
                venta.total_iva_5 = request.POST['total_iva_5']
                venta.id_cliente = Cliente.objects.get(id_cliente=request.POST['cliente'])
                venta.total_venta = request.POST['total_venta']
                venta.fecha_venta = fecha_venta
                venta.id_tipo_venta = TipoVenta.objects.get(id=id_tipo_venta)
                venta.usuario_creacion = request.user.id
                venta.save()

                VentaDetalle.objects.filter(id_venta=venta).delete()
                VentaTipoDePago.objects.filter(id_venta=venta).delete()
                _guardar_detalles_y_pagos(
                    venta, request.POST.get('productos_json'),
                    pago_efectivo, pago_pos, pago_transferencia,
                )

            messages.success(request, f"Venta #{venta.id_venta} actualizada")
            return redirect('ventas:ventas')
        except Exception as e:
            error_message = str(e)
            messages.error(request, f"Error al registrar venta {error_message}")
            logging.error(f'Error al editar venta: {error_message}')
            return redirect(reverse('ventas:editar_venta', args=[id_venta]))

    venta = get_object_or_404(Venta, id_venta=id_venta)
    pagos = {1: 0, 2: 0, 3: 0}
    for pago in VentaTipoDePago.objects.filter(id_venta=id_venta):
        pagos[pago.id_tipo_pago_id] = pago.monto

    carrito_inicial = [
        {'id': detalle.id_producto_id, 'cantidad': detalle.cantidad_producto}
        for detalle in VentaDetalle.objects.filter(id_venta=id_venta).order_by('id_detalle')
    ]

    context = _contexto_formulario_venta(venta)
    context.update({
        'venta': venta,
        'carrito_inicial': carrito_inicial,
        'pagos_iniciales': {'efectivo': pagos[1], 'pos': pagos[2], 'transferencia': pagos[3]},
    })
    return render(request, 'ventas/editar_venta.html', context=context)


@login_required(login_url="/")
@permission_required("ventas.delete_venta", login_url="/")
@require_POST
def ventasDeleteView(request, id_venta):
    venta = get_object_or_404(Venta, pk=id_venta)

    if _venta_tiene_factura(id_venta):
        messages.warning(request, MENSAJE_VENTA_BLOQUEADA.format(accion='eliminar'))
        return redirect('ventas:ventas')

    if venta:

        detalles = VentaDetalle.objects.filter(id_venta=id_venta)

        for detalle in detalles:
            detalle.delete()

        ventas_tipo_pago = VentaTipoDePago.objects.filter(id_venta=id_venta)

        for pago in ventas_tipo_pago:
            pago.delete()

        venta.delete()
    return redirect('ventas:ventas')


@login_required(login_url="/")
def ventaDetalleView(request, id_venta):
    venta = get_object_or_404(Venta, id_venta=id_venta)
    detalle_venta = VentaDetalle.objects.filter(id_venta=id_venta)
    context = {
        'venta': venta,
        'detalle_venta': detalle_venta,
    }
    return render(request, 'ventas/detalle_venta.html', context=context)


@login_required(login_url="/")
def historialDeVentasView(request):
    ventas_agrupadas = Venta.objects.annotate(fecha=TruncDate('fecha_venta')) \
        .values('fecha') \
        .annotate(total_ventas=Sum('total_venta')) \
        .order_by('-fecha')

    paginator = Paginator(ventas_agrupadas, 10)
    page_number = request.GET.get('page', 1)
    ventas_por_pagina = paginator.get_page(page_number)
    context = {
        'ventas_agrupadas': ventas_por_pagina
    }

    return render(request, 'ventas/ventas_historial.html', context=context)

import json
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.factura.models import Factura
from apps.productos.models import Producto
from apps.tipo_pago.models import TipoPago
from apps.ventas.forms import *
from apps.ventas.models import VentaTipoDePago, TipoVenta


def _es_tipo_venta_pedidos_ya(tipo_venta):
    return bool(tipo_venta and 'pedido' in tipo_venta.nombre.lower())


def _obtener_precio_producto_por_tipo_venta(producto, tipo_venta):
    if _es_tipo_venta_pedidos_ya(tipo_venta):
        return float(producto.precio_pedidos_ya or producto.precio_actual or 0)
    return float(producto.precio_actual or 0)


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

    facturas_emitidas = Factura.objects.filter(
        id_venta__in=ids_ventas,
        estado=Factura.ESTADO_EMITIDA
    ).select_related('id_venta')
    factura_por_venta = {factura.id_venta_id: factura for factura in facturas_emitidas}

    # Agregar atributo dinámico a cada venta
    for venta in ventas:
        venta.formas_pago = ", ".join(formas_pago_dict.get(venta.id_venta, []))
        factura = factura_por_venta.get(venta.id_venta)
        venta.factura_emitida = factura is not None
        venta.id_factura_emitida = factura.id_factura if factura else None

    # Filtrar los pagos con id_tipo_pago=1 y los id_venta obtenidos
    pagos_efectivo = VentaTipoDePago.objects.filter(id_tipo_pago=1, id_venta__in=ids_ventas)

    # Obtener solo los montos (opcional)
    montos_efectivo = pagos_efectivo.values_list('monto', flat=True)

    # Si necesitas sumarlos
    total_monto_efectivo = pagos_efectivo.aggregate(total=Sum('monto'))['total']
    print(f'fecha: {fecha_venta}, ventas: {ventas}')
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
    }

    return render(request, 'ventas/ventas.html', context=context)


@login_required(login_url="/")
def ventasCreateView(request):
    # Se cargan los productos para mostrar en la lista
    productos = Producto.objects.all()
    clientes = Cliente.objects.all()
    tipos_de_pago = TipoPago.objects.all()
    tipo_venta = TipoVenta.objects.all()
    # print(f'productos: {productos}')

    if request.method == 'POST':
        # form = VentaForm(request.POST)
        # if form.is_valid():
        try:
            print("Ingresa al metodo POST", request.POST)
            total_iva_10 = request.POST['total_iva_10']
            total_iva_5 = request.POST['total_iva_5']
            id_cliente = request.POST['cliente']
            total_venta = request.POST['total_venta']
            pago_pos = float(request.POST.get('pos', 0) or 0)
            pago_efectivo = float(request.POST.get('efectivo', 0) or 0)
            pago_transferencia = float(request.POST.get('transferencia', 0) or 0)
            fecha_venta_str = request.POST.get('fecha_venta')
            id_tipo_venta = request.POST.get('tipo_venta')

            # Si el usuario no toca nada, queda la actual
            if fecha_venta_str:
                fecha_venta = datetime.strptime(fecha_venta_str, "%Y-%m-%dT%H:%M")
            else:
                fecha_venta = timezone.now()

            nueva_venta = Venta.objects.create(
                fecha_venta=fecha_venta,
                total_iva_10=total_iva_10,
                total_iva_5=total_iva_5,
                id_cliente=Cliente.objects.get(id_cliente=id_cliente),
                total_venta=total_venta,
                usuario_creacion=request.user.id,
                id_tipo_venta=TipoVenta.objects.get(id=id_tipo_venta),
            )

            nueva_venta.save()
            productos_json = request.POST.get('productos_json')
            productos_data = json.loads(productos_json)  # Convertir JSON en lista de diccionarios

            for detalle in productos_data:
                id_producto = detalle['id_producto']
                cantidad_producto = detalle['cantidad']
                total_detalle = detalle['total_detalle']
                total_iva_10 = detalle['total_detalle_iva_10']
                total_iva_5 = detalle['total_detalle_iva_5']

                # Crear y guardar cada detalle de venta
                venta_detalle = VentaDetalle.objects.create(
                    id_venta=nueva_venta,
                    id_producto=Producto.objects.get(id_producto=id_producto),
                    cantidad_producto=cantidad_producto,
                    total_detalle=total_detalle,
                    total_iva_5=total_iva_5,
                    total_iva_10=total_iva_10
                )
                venta_detalle.save()

            if pago_pos > 0:
                venta_tipo_pago = VentaTipoDePago.objects.create(
                    id_venta=nueva_venta,
                    id_tipo_pago=TipoPago.objects.get(id_tipo_pago=2),
                    monto=pago_pos,
                )
                venta_tipo_pago.save()

            if pago_efectivo > 0:
                venta_tipo_pago = VentaTipoDePago.objects.create(
                    id_venta=nueva_venta,
                    id_tipo_pago=TipoPago.objects.get(id_tipo_pago=1),
                    monto=pago_efectivo,
                )
                venta_tipo_pago.save()

            if pago_transferencia > 0:
                venta_tipo_pago = VentaTipoDePago.objects.create(
                    id_venta=nueva_venta,
                    id_tipo_pago=TipoPago.objects.get(id_tipo_pago=3),
                    monto=pago_transferencia,
                )
                venta_tipo_pago.save()

            messages.success(request, "Venta registrada exitosamente")
            return redirect('ventas:ventas')
        except Exception as e:
            error_message = str(e)
            messages.error(request, "Error al registrar venta {error_message}")
            logging.error(f'Error al crear venta: {error_message}')
            return redirect('ventas:crear_venta')

    context = {
        'productos': productos,
        'clientes': clientes,
        'tipos_de_pago': tipos_de_pago,
        'now': timezone.now(),
        "tipo_venta": tipo_venta
    }

    return render(request, 'ventas/crear_venta.html', context=context)


@login_required(login_url="/")
def ventasEditView(request, id_venta):
    if request.method == 'POST':
        try:
            print("Ingresa al metodo POST")
            total_iva_10 = request.POST['total_iva_10']
            total_iva_5 = request.POST['total_iva_5']
            id_cliente = request.POST['cliente']
            total_venta = request.POST['total_venta']
            pago_pos = float(request.POST.get('pos', 0) or 0)
            pago_efectivo = float(request.POST.get('efectivo', 0) or 0)
            pago_transferencia = float(request.POST.get('transferencia', 0) or 0)
            fecha_venta_str = request.POST.get('fecha_venta')
            id_tipo_venta = request.POST.get('tipo_venta')
            if not id_tipo_venta:
                raise ValueError("Debes seleccionar un tipo de venta.")
            venta = get_object_or_404(Venta, id_venta=id_venta)
            print(f'nueva venta: {venta}')

            if fecha_venta_str:
                fecha_venta = datetime.strptime(fecha_venta_str, "%Y-%m-%dT%H:%M")
            else:
                fecha_venta = timezone.now()

            venta.total_iva_10 = total_iva_10
            venta.total_iva_5 = total_iva_5
            venta.id_cliente = Cliente.objects.get(id_cliente=id_cliente)
            venta.total_venta = total_venta
            venta.fecha_venta = fecha_venta
            venta.id_tipo_venta = TipoVenta.objects.get(id=id_tipo_venta) if id_tipo_venta else None
            venta.usuario_creacion = request.user.id
            venta.save()

            # Se obtienen los detalles para eliminarlos 
            detalles = VentaDetalle.objects.filter(id_venta=id_venta)
            for detalle in detalles:
                detalle.delete()

            # Se obtienen la lista nueva de productos
            productos_json = request.POST.get('productos_json')
            if not productos_json:
                raise ValueError("No se recibieron los detalles de la venta.")
            productos_data = json.loads(productos_json)  # Convertir JSON en lista de diccionarios
            for detalle in productos_data:
                id_producto = detalle['id_producto']
                cantidad_producto = detalle['cantidad']
                total_detalle = detalle['total_detalle']
                total_iva_10 = detalle['total_detalle_iva_10']
                total_iva_5 = detalle['total_detalle_iva_5']

                # Crear y guardar cada detalle de venta 
                venta_detalle = VentaDetalle.objects.create(
                    id_venta=venta,
                    id_producto=Producto.objects.get(id_producto=id_producto),
                    cantidad_producto=cantidad_producto,
                    total_detalle=total_detalle,
                    total_iva_5=total_iva_5,
                    total_iva_10=total_iva_10
                )
                venta_detalle.save()

            VentaTipoDePago.objects.filter(id_venta=venta).delete()

            if pago_pos > 0:
                venta_tipo_pago = VentaTipoDePago.objects.create(
                    id_venta=venta,
                    id_tipo_pago=TipoPago.objects.get(id_tipo_pago=2),
                    monto=pago_pos,
                )
                venta_tipo_pago.save()

            if pago_efectivo > 0:
                venta_tipo_pago = VentaTipoDePago.objects.create(
                    id_venta=venta,
                    id_tipo_pago=TipoPago.objects.get(id_tipo_pago=1),
                    monto=pago_efectivo,
                )
                venta_tipo_pago.save()

            if pago_transferencia > 0:
                venta_tipo_pago = VentaTipoDePago.objects.create(
                    id_venta=venta,
                    id_tipo_pago=TipoPago.objects.get(id_tipo_pago=3),
                    monto=pago_transferencia,
                )
                venta_tipo_pago.save()

            return redirect('ventas:ventas')
        except Exception as e:
            error_message = str(e)
            messages.error(request, f"Error al registrar venta {error_message}")
            logging.error(f'Error al crear venta: {error_message}')
            return redirect(reverse('ventas:editar_venta', args=[id_venta]))
    else:
        venta = get_object_or_404(Venta, id_venta=id_venta)
        detalle_venta = VentaDetalle.objects.filter(id_venta=id_venta)
        detalle_tipo_pago = VentaTipoDePago.objects.filter(id_venta=id_venta)
        monto_efectivo = 0
        monto_pos = 0
        monto_transferencia = 0

        for pago in detalle_tipo_pago:
            if pago.id_tipo_pago_id == 1:
                monto_efectivo = pago.monto
            elif pago.id_tipo_pago_id == 2:
                monto_pos = pago.monto
            elif pago.id_tipo_pago_id == 3:
                monto_transferencia = pago.monto

        detalles_serializados = []
        for detalle in detalle_venta:
            precio_unitario = _obtener_precio_producto_por_tipo_venta(detalle.id_producto, venta.id_tipo_venta)
            detalle.precio_unitario_venta = precio_unitario
            detalles_serializados.append({
                'id_producto': detalle.id_producto.id_producto,
                'cantidad': detalle.cantidad_producto,
                'precioUnitario': float(precio_unitario),
                'totalDetalle': float(detalle.total_detalle),
                'ivaDescripcion': int(detalle.id_producto.id_iva.descripcion),
                'total_iva_10': float(detalle.total_iva_10),
                'total_iva_5': float(detalle.total_iva_5),
                'nombre': detalle.id_producto.nombre
            })

        clientes = Cliente.objects.all()
        productos = Producto.objects.all()
        tipo_venta = TipoVenta.objects.all()
        context = {
            'venta': venta,
            'clientes': clientes,
            'detalle_venta': detalle_venta,
            'productos': productos,
            'detalle_tipo_pago': detalle_tipo_pago,
            'detalle_venta_json': json.dumps(detalles_serializados, cls=DjangoJSONEncoder),
            'tipo_venta': tipo_venta,
            'monto_efectivo': monto_efectivo,
            'monto_pos': monto_pos,
            'monto_transferencia': monto_transferencia,
        }
    return render(request, 'ventas/editar_venta.html', context=context)


@login_required(login_url="/")
def ventasDeleteView(request, id_venta):
    venta = get_object_or_404(Venta, pk=id_venta)

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

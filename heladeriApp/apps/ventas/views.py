import json
from django.contrib import messages
import logging
from django.shortcuts import get_object_or_404, redirect, render
from apps.ventas.forms import *
from apps.productos.models import Producto
from apps.clientes.models import Cliente
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage
from django.db.models import Sum
from django.utils import timezone

from apps.tipo_pago.models import TipoPago

def ventasReadView(request):
    today = timezone.localdate()
    ventas = Venta.objects.filter(fecha_venta__date=today).order_by('id_venta')
    print(f'fecha: {today}, ventas: {ventas}')
    total_ventas = ventas.aggregate(total_ventas=Sum('total_venta'))['total_ventas'] or 0
    total_ventas_caja = ventas.filter(id_tipo_pago=1).aggregate(total_ventas=Sum('total_venta'))['total_ventas'] or 0
    ventas_todas = Venta.objects.all()
    for venta in ventas_todas:
        print("id: ",venta.id_venta ,"fecha: " ,venta.fecha_venta)

    columnas = ['Cliente','Total venta', 'Total IVA 10', 'Total IVA 5','Tipo','Fecha']
    paginator = Paginator(ventas,10)
    page_number = request.GET.get('page',1)
    ventas_por_pagina=paginator.get_page(page_number)

    context = {
        'columnas':columnas,
        'ventas_por_pagina' :ventas_por_pagina,
        'total_ventas': total_ventas,
        'total_ventas_caja':total_ventas_caja
    }

    return render(request, 'ventas/ventas.html', context=context)

def ventasCreateView(request):
    # Se cargan los productos para mostrar en la lista
    productos = Producto.objects.all()
    clientes = Cliente.objects.all()
    tipos_de_pago = TipoPago.objects.all()
    print(f'productos: {productos}')
    
    if request.method == 'POST':
        #form = VentaForm(request.POST)
        #if form.is_valid():
        try:
            print("Ingresa al metodo POST")   
            total_iva_10 = request.POST['total_iva_10']
            total_iva_5 = request.POST['total_iva_5']
            id_cliente =  request.POST['cliente']
            id_tipo_pago = request.POST['tipo_de_pago']
            total_venta = request.POST['total_venta']
            nueva_venta = Venta.objects.create(
                total_iva_10 = total_iva_10,
                total_iva_5 = total_iva_5,
                id_cliente = Cliente.objects.get(id_cliente=id_cliente),
                id_tipo_pago = TipoPago.objects.get(id_tipo_pago=id_tipo_pago),
                total_venta = total_venta,
                usuario_creacion = request.user.id
            )
            print(f'nueva venta: {nueva_venta}')
            nueva_venta.save()
            productos_json = request.POST.get('productos_json')
            productos_data = json.loads(productos_json)  # Convertir JSON en lista de diccionarios
            
            for detalle in productos_data:
                id_producto = detalle['id_producto']
                cantidad_producto = detalle['cantidad']
                total_detalle = detalle['total_detalle']
                
                # Crear y guardar cada detalle de venta
                venta_detalle = VentaDetalle.objects.create(
                    id_venta=nueva_venta,
                    id_producto=Producto.objects.get(id_producto=id_producto),
                    cantidad_producto=cantidad_producto,
                    total_detalle=total_detalle
                )
                venta_detalle.save()

            return redirect('ventas:ventas')
        except Exception as e:
            error_message = str(e)
            messages.error(request, "Error al registrar venta {error_message}")
            logging.error(f'Error al crear venta: {error_message}') 
            return redirect('ventas:crear_venta')  
        #else:
        #    print("formulario no valido") 
    #else:
    #    messages.success(request,"Se arma el formulario")
    #    form = VentaForm()
    context = {
        'productos':productos,
        'clientes':clientes,
        'tipos_de_pago':tipos_de_pago
        #'form':form
    }
        
    return render(request, 'ventas/crear_venta.html', context=context)

def ventasEditView(request,id_venta):
    venta = Venta.objects.filter(id_venta = id_venta)
    clientes = Cliente.objects.all()
    tipos_de_pago = TipoPago.objects.all()
    context = {
        'venta':venta,
        'clientes': clientes,
    }


def ventasDeleteView(request, id_venta):
    venta = get_object_or_404(Venta, pk=id_venta)
    
    if venta:

        detalles = VentaDetalle.objects.filter(id_venta = id_venta)

        for detalle in detalles:
            detalle.delete()

        venta.delete()
    return redirect('ventas:ventas')
import json
from django.contrib import messages
import logging
from django.shortcuts import redirect, render
from apps.ventas.forms import *
from apps.productos.models import Producto
from apps.clientes.models import Cliente

def ventasReadView(request):
    ventas = Venta.objects.all()
    columnas = ['Cliente','Total venta', 'Total IVA 10', 'Total IVA 5','Fecha','Usuario']
    context = {
        'columnas':columnas,
        'ventas':ventas
    }

    return render(request, 'ventas/ventas.html', context=context)

def ventasCreateView(request):
    # Se cargan los productos para mostrar en la lista
    productos = Producto.objects.all()
    clientes = Cliente.objects.all()
    print(f'productos: {productos}')
    
    if request.method == 'POST':
        #form = VentaForm(request.POST)
        #if form.is_valid():
        try:
            print("Ingresa al metodo POST")   
            total_iva_10 = request.POST['total_iva_10']
            total_iva_5 = request.POST['total_iva_5']
            id_cliente =  request.POST['cliente']
            total_venta = request.POST['total_venta']
            nueva_venta = Venta.objects.create(
                total_iva_10 = total_iva_10,
                total_iva_5 = total_iva_5,
                id_cliente = Cliente.objects.get(id_cliente=id_cliente),
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
        'clientes':clientes
        #'form':form
    }
        
    return render(request, 'ventas/crear_venta.html', context=context)
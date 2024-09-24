import logging
from django.shortcuts import render,redirect
from django.contrib import messages
from .forms import *
from django.core.paginator import Paginator

def productosReadView(request):
    productos = Producto.objects.select_related('id_medida').all()
    columnas = ['Nombre','Precio Actual','Stock Minimo','Stock Actual','Vencimiento','Costo Actual','Medida']
    paginator = Paginator(productos,10)
    page_number = request.GET.get('page')
    items_page=paginator.get_page(page_number)
    context = {
        'columnas':columnas,
        'productos':productos,
        'items_page': items_page
    }
    
    return render(request, 'productos/productos.html', context=context)

def createProductosView(request):
    if request.method == 'POST':
        form = ProductosForm(request.POST)
        if form.is_valid():
            try:
                nombre = request.POST['nombre']
                precio_actual = request.POST['precio_actual']
                stock_minimo = request.POST['stock_minimo']
                stock_actual = request.POST['stock_actual']
                vencimiento = request.POST['vencimiento']
                costo_actual = request.POST['costo_actual']
                id_medida = Medida.objects.get(id_medida=request.POST['medida'])
                id_iva = Iva.objects.get(id_iva=request.POST['iva'])

                productoNuevo = Producto.objects.create(
                    nombre =nombre,
                    precio_actual = precio_actual,
                    stock_minimo= stock_minimo,
                    stock_actual = stock_actual, 
                    vencimiento = vencimiento,
                    costo_actual = costo_actual,
                    usuario_creacion = request.user.id,
                    id_iva = id_iva,
                    id_medida = id_medida
                )
                productoNuevo.save()
                messages.success(request, 'Producto creado exitosamente')
                return redirect('productos:productos')
            except Exception as e:
                error_message = str(e)  # Captura el mensaje de error
                messages.error(request, f'Error en el servidor: {error_message}')
                logging.error(f'Error al crear producto: {error_message}')  # O puedes registrar el error en un archivo de log
                return redirect('productos:productos')
    else:
        form = ProductosForm()

    return render(request,'productos/crear_productos.html',{'form':form})
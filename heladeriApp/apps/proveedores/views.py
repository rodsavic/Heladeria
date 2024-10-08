import logging
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from .forms import *
from .models import Proveedor
from django.core.paginator import Paginator

def proveedorReadView(request):
    proveedores = Proveedor.objects.all()
    columnas = ['Documento/RUC','Nombre','Direccion','Correo','Estado','Telefono','Operaciones']
    paginator = Paginator(proveedores,10)
    page_number = request.GET.get('page',1)
    proveedores_por_pagina=paginator.get_page(page_number)
    context = {
        'proveedores':proveedores,
        'proveedores_por_pagina':proveedores_por_pagina,
        'columnas': columnas
    }

    return render(request, 'proveedores/proveedores.html', context=context)

def createProveedorView(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            documento = request.POST['documento']
            nombre = request.POST['nombre']
            telefono = request.POST['telefono']
            direccion = request.POST['direccion']
            correo = request.POST['correo']
            usuario_creacion = request.user.id

            try:
                nuevo_proveedor = Proveedor.objects.create(
                    documento=documento,
                    nombre=nombre,
                    telefono=telefono,
                    direccion=direccion,
                    correo=correo,
                    usuario_creacion=usuario_creacion
                )

                nuevo_proveedor.save()
                messages.success(request,'Proveedor creado exitosamente')
            except Exception as e:
                error_message = str(e) 
                messages.error(request, f'Error en el servidor: {error_message}')
                logging.error(f'Error al crear proveedor: {error_message}') 
                return redirect('proveedores:proveedores')
        else:
            messages.error(request, 'Error en el formulario')
            return redirect('proveedores:crear_proveedor')
    else:
        form = ProveedorForm()

    return render(request, 'proveedores/crear_proveedor.html', {'form':form})         

def proveedorUpdateView(request, id_proveedor):
    """Vista para modificar proveedor"""
    proveedor = Proveedor.objects.get(id_proveedor=id_proveedor)
    # Si se desea guardar en la BDD
    if request.method == 'POST':
        # Creamos una instancia de formulario y la llenamos con el data del request:
        form = ProveedorForm(request.POST, instance=proveedor)
        # Si no se han hecho modificaciones
        if not form.has_changed():
            messages.info(request, "No ha hecho ningun cambio", extra_tags=" ")
            return redirect('proveedores:proveedores')
        # Verificamos que los datos sean validos:
        if form.is_valid():
            form.save()
            messages.success(request, 'proveedor: ' +
                             request.POST['nombre'] + ' modificado exitosamente!', extra_tags=" ")
            return redirect('proveedores:proveedores')
        else:
            # Datos invalidos en el formulario, renderizamos de nuevo con los errores
            if 'documento' in form.errors:
                messages.info(request, 'El documento ya existe!',
                              extra_tags="Verifica e intenta de nuevo.")
            return render(request, 'proveedores/editar_proveedor.html',
                          {'form': form, 'proveedor': proveedor})
    else:
        # Si es una solicitud GET envia el template
        context = {
            'form': ProveedorForm(instance=proveedor),
            'proveedor': proveedor
        }
        return render(request, 'proveedores/editar_proveedor.html', context=context)

def proveedorDeleteView(request, id_proveedor):
    proveedor = get_object_or_404(Proveedor, pk=id_proveedor)
    proveedor.delete()
    messages.success(request,"Proveedor eliminado correctamente")
    return redirect('proveedores:proveedores')   

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import *
from .models import Proveedor

def proveedorReadView(request):
    proveedores = Proveedor.objects.all()
    context = {
        'proveedores':proveedores
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
            return redirect('proveedores:proveedores')
    else:
        form = ProveedorForm()

    return render(request, 'proveedores/crear_proveedor.html', {'form':form})            

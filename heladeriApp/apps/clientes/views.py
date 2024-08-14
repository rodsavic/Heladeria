from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from django.contrib import messages
from .forms import *
from .models import *

@login_required(login_url="/authentication/login")
def clienteReadView(request):
    clientes = Cliente.objects.all()
    columnas = ["Nombre", "Apellido", "Correo","Cédula","Número", "Dirección", "Estado"]
    context = {
        'columnas':columnas,
        'clientes':clientes
    }
    return render(request, "clientes/clientes.html", context=context)

@login_required(login_url="/authentication/login")
def crearCliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            try:
                documento = request.POST['documento']
                nombre = request.POST['nombre']
                apellido = request.POST['apellido']
                correo = request.POST['correo']
                celular = request.POST['celular']
                direccion = request.POST['direccion']

                cliente_nuevo = Cliente.objects.create(
                    documento= documento,
                    nombre = nombre,
                    apellido = apellido,
                    correo = correo,
                    celular = celular,
                    direccion = direccion,
                    estado = 'Activo'
                )

                cliente_nuevo.save()
                messages.success(request, "Cliente creado con exito")
                return redirect("clientes:clientes")
            except:
                messages.error(request,"Error en el servidor")
                return redirect("clientes:clientes")
        else:
            messages.error(request, "El formulario no es valido")
    else:
        form = ClienteForm()

    return render(request, "clientes/crear_cliente.html", {'form':form})
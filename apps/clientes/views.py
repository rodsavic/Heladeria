from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render,redirect
from django.contrib import messages
from django.core.paginator import Paginator
from .forms import *
from .models import *

@login_required(login_url="/")
def clienteReadView(request):
    clientes = Cliente.objects.all().order_by('nombre')
    columnas = ["Nombre", "Apellido", "Correo","Cédula","Número", "Dirección", "Estado"]
    paginator = Paginator(clientes,10)
    page_number = request.GET.get('page')
    items_page=paginator.get_page(page_number)
    context = {
        'columnas':columnas,
        'clientes':clientes,
        'items_page': items_page
    }
    return render(request, "clientes/clientes.html", context=context)

@login_required(login_url="/")
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


@login_required(login_url="/")
def crearClienteAjax(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'message': 'Metodo no permitido'}, status=405)

    form = ClienteForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    try:
        cliente_nuevo = Cliente.objects.create(
            documento=request.POST['documento'],
            nombre=request.POST['nombre'],
            apellido=request.POST['apellido'],
            correo=request.POST['correo'],
            celular=request.POST['celular'],
            direccion=request.POST['direccion'],
            estado='Activo'
        )
        return JsonResponse({
            'ok': True,
            'cliente': {
                'id_cliente': cliente_nuevo.id_cliente,
                'nombre': cliente_nuevo.nombre,
                'apellido': cliente_nuevo.apellido,
                'documento': cliente_nuevo.documento,
                'label': f'{cliente_nuevo.nombre} - {cliente_nuevo.documento}'
            }
        })
    except Exception:
        return JsonResponse({'ok': False, 'message': 'Error en el servidor'}, status=500)


@login_required(login_url="/")
def clientesJson(request):
    clientes = list(
        Cliente.objects.order_by('nombre').values(
            'id_cliente',
            'nombre',
            'apellido',
            'documento',
        )
    )
    for cliente in clientes:
        cliente['label'] = f"{cliente['nombre']} - {cliente['documento']}"
    return JsonResponse({'clientes': clientes})

@login_required(login_url="/")
def clienteUpdateView(request, id_cliente):
    """Vista para modificar cliente"""
    cliente = Cliente.objects.get(id_cliente=id_cliente)
    # Si se desea guardar en la BDD
    if request.method == 'POST':
        # Creamos una instancia de formulario y la llenamos con el data del request:
        form = ClienteForm(request.POST, instance=cliente)
        # Si no se han hecho modificaciones
        if not form.has_changed():
            messages.info(request, "No ha hecho ningun cambio", extra_tags=" ")
            return redirect('clientes:clientes')
        # Verificamos que los datos sean validos:
        if form.is_valid():
            form.save()
            messages.success(request, 'cliente: ' +
                             request.POST['nombre'] + ' modificado exitosamente!', extra_tags=" ")
            return redirect('clientes:clientes')
        else:
            # Datos invalidos en el formulario, renderizamos de nuevo con los errores
            if 'nombre' in form.errors:
                messages.info(request, 'El nombre ya existe!',
                              extra_tags="Verifica e intenta de nuevo.")
            return render(request, 'clientes/editar_cliente.html',
                          {'form': form, 'cliente': cliente})
    else:
        # Si es una solicitud GET envia el template
        context = {
            'form': ClienteForm(instance=cliente),
            'cliente': cliente
        }
        return render(request, 'clientes/editar_cliente.html', context=context)

@login_required(login_url="/")
def clienteDeleteView(request, id_cliente):
    cliente = get_object_or_404(Cliente, pk=id_cliente)
    cliente.delete()
    messages.success(request,"Cliente eliminado correctamente")
    return redirect('clientes:clientes')

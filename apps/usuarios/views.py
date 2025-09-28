from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from .forms import *
from .models import *
import json

@login_required(login_url="/")
def usuariosReadView(request):

    # Obtener los campos de los usuarios
    usuarios = User.objects.all().order_by('username')
    columnas = ["Usuario","Nombre", "Apellido","Accion"]
    paginator = Paginator(usuarios,10)
    page_number = request.GET.get('page')
    usuarios_por_pagina=paginator.get_page(page_number)
    print(f'{usuarios}')
    context = {
        "columnas":columnas,
        "usuarios": usuarios,
        'usuarios_por_pagina':usuarios_por_pagina
    }
    return render(request, "usuarios/usuarios.html", context=context)


@login_required(login_url="/")
def usuarioReadView(request):

    usuario_q = User.objects.filter(username=request.user.username).first()

    context = {
        "usuario": usuario_q,
    }

    return render(request, "usuarios/perfil.html", context=context)


@login_required(login_url="/")
def createUserView(request):

    # Obtenemos la lista de permisos
    lista_grupos_id = list(Group.objects.values_list('id', flat=True))
    lista_grupos_nombre = list(Group.objects.values_list('name', flat=True))
    lista_grupo_dict = []

    # Creamos diccionario con el id y el nombre para select2
    for i in range(len(lista_grupos_id)):
        id_grupo = lista_grupos_id[i]
        nombre_grupo = lista_grupos_nombre[i]
        lista_grupo_dict.append({"id": id_grupo, "text": nombre_grupo})

    lista_grupos_json = json.dumps(lista_grupo_dict)

    print(lista_grupos_json)

    context = {
        "grupos_json": lista_grupo_dict
    }

    # Si se desea guardar en la BDD
    if request.method == 'POST':

        # Obtiene los argumentos enviados para crear el usuario
        username = request.POST['username']
        nombre = request.POST['nombre']
        direccion = request.POST['direccion']
        telefono = request.POST['telefono']
        fecha_nacimiento = request.POST['fecha_nacimiento']
        apellido = request.POST['apellido']
        password = request.POST['password']
        password_repetir = request.POST['password_repetir']
        correo = request.POST['correo']
        grupo = request.POST.getlist('grupo')

        print(request.POST)

        # Verificamos que el username no exista
        if User.objects.filter(username=username).exists():
            messages.info(request, 'El username ya existe!',
                          extra_tags="Verifica el username e intenta de nuevo.")
            return redirect(reverse('usuarios:usuarios-create'))

        # Verificamos que las contraseñas coincidan
        if password != password_repetir:
            messages.warning(request, 'Las contraseñas no coinciden!',
                          extra_tags="Verifica e intenta de nuevo.")
            return redirect(reverse('usuarios:usuarios-create'))            

        # Verificamos que la contraseña no sea muy corta
        if len(password) < 5:
            messages.warning(request, 'La contraseña es demasiada corta!',
                          extra_tags="Verifica e intenta de nuevo.")
            return redirect(reverse('usuarios:usuarios-create'))                  

        # Creamos y guardamos el usuario
        usuario_nuevo = User.objects.create(
            username=username,
            first_name=nombre,
            last_name=apellido,
            email=correo,
            telefono=telefono,
            direccion=direccion,
            fecha_nacimiento=fecha_nacimiento,
            usuario_creacion=request.user.id,
            password=make_password(password))

        # Agregamos grupos
        if len(grupo) > 0:
            for g in grupo:
                usuario_nuevo.groups.add(g)

        usuario_nuevo.save()

        messages.success(request, 'Usuario ' +
                         nombre + ' creado exitosamente!', extra_tags=" ")
        return redirect('usuarios:usuarios')

    # Si es una solicitud GET envia el template
    else:
        return render(request, 'usuarios/usuarios_create.html', context=context)


@login_required(login_url="/")
def usuarioUpdateView(request, id):
    usuario = User.objects.get(id=id)

    # Obtener los grupos disponibles para el select2
    lista_grupos_id = list(Group.objects.values_list('id', flat=True))
    lista_grupos_nombre = list(Group.objects.values_list('name', flat=True))
    lista_grupo_dict = []

    for i in range(len(lista_grupos_id)):
        lista_grupo_dict.append({
            "id": lista_grupos_id[i],
            "text": lista_grupos_nombre[i]
        })

    grupos_json = json.dumps(lista_grupo_dict)

    if request.method == 'POST':
        username = request.POST['username']
        nombre = request.POST['nombre']
        direccion = request.POST['direccion']
        telefono = request.POST['telefono']
        fecha_nacimiento = request.POST['fecha_nacimiento']
        apellido = request.POST['apellido']
        password = request.POST['password']
        password_repetir = request.POST['password_repetir']
        correo = request.POST['correo']
        grupo = request.POST.getlist('grupo')

        if password and password != password_repetir:
            messages.warning(request, 'Las contraseñas no coinciden!',
                             extra_tags="Verifica e intenta de nuevo.")
            return redirect(reverse('usuarios:usuarios_modificar', args=[id]))

        if password and len(password) < 5:
            messages.warning(request, 'La contraseña es demasiado corta!',
                             extra_tags="Verifica e intenta de nuevo.")
            return redirect(reverse('usuarios:usuarios_modificar', args=[id]))

        try:
            # Actualizar datos del usuario
            usuario.first_name = nombre
            usuario.last_name = apellido
            usuario.username = username
            usuario.email = correo
            usuario.telefono = telefono
            usuario.direccion = direccion
            usuario.fecha_nacimiento = fecha_nacimiento

            if password:
                usuario.contrasena = make_password(password)

            usuario.save()

            # Actualizar grupos
            usuario_django = User.objects.get(username=username)
            usuario_django.groups.clear()
            if len(grupo) > 0:
                for g in grupo:
                    usuario_django.groups.add(g)

            messages.success(request, 'Usuario actualizado exitosamente!')
            return redirect('usuarios:usuarios')

        except Exception as e:
            messages.error(request, f"Ocurrió un error: {str(e)}")
            return redirect(reverse('usuarios:usuarios_modificar', args=[id]))

    else:
        # Preparar datos del usuario para el formulario
        usuario_django = User.objects.get(username=usuario.username)
        grupos_usuario = usuario_django.groups.values_list('id', flat=True)

        context = {
            "usuario": usuario,
            "grupos_json": lista_grupo_dict,
            "grupos_usuario": list(grupos_usuario)
        }
        return render(request, "usuarios/usuarios_modificar.html", context)


@login_required(login_url="/")
def crearRol(request):
    if request.method == 'POST':
        nombre = request.POST.get('name')
        permisos_ids = request.POST.getlist('permissions') 

        if nombre:
            nuevo_grupo = Group.objects.create(name=nombre)
            if permisos_ids:
                permisos = Permission.objects.filter(id__in=permisos_ids)
                nuevo_grupo.permissions.set(permisos)
            return redirect('usuarios:roles')
        else:
            pass

    permisos = Permission.objects.all()
    permisos_data = [{"id": permiso.id, "text": permiso.name} for permiso in permisos]

    context = {
        "permisos_json": json.dumps(permisos_data) 
    }
    return render(request, 'usuarios/crear_rol.html', context)


@login_required(login_url="/")
def rolReadView(request):
    roles = Group.objects.all().prefetch_related('permissions')

    context = {
        'roles': roles
    }
    return render(request, 'usuarios/roles.html', context=context)


@login_required(login_url="/")
def crearPermiso(request):
    if request.method == 'POST':
        form = PermisoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"El permiso fue creado exitosamente")
            return redirect('usuarios:permisos')
        else:
            messages.error(request, "Hubo un error al crear el permiso")
            return redirect('usuarios:permisos')
    else:
        form = PermisoForm()

    return render(request, 'usuarios/crear_permiso.html', {'form': form})

@login_required(login_url="/")
def permisoReadView(request):
    permisos = Permiso.objects.all()
    paginator = Paginator(permisos,10)
    page_number = request.GET.get('page')
    permisos_por_pagina=paginator.get_page(page_number)
    context = {
        'permisos':permisos,
        'permisos_por_pagina':permisos_por_pagina,
    }

    return render(request, 'usuarios/permisos.html', context=context)
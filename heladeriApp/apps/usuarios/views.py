from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from django.core.paginator import Paginator
from .forms import *
from .models import *

@login_required(login_url="/authentication/login")
def usuariosReadView(request):

    # Obtener los campos de los usuarios
    usuarios = Usuario.objects.all().order_by('nombre')
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



@login_required(login_url="/authentication/login")
def crearUsuario(request):
    # Vista para crear usuarios
    if request.method == "POST":
        form = UsuarioForm(request.POST)

        if form.is_valid():
            try:
                # Obtener el usuario actual
                usuario_actual = Usuario.objects.get(nombre_usuario=request.user)

                # Crear el nuevo usuario utilizando los datos validados del formulario
                usuario_nuevo = Usuario.objects.create(
                    nombre=form.cleaned_data["nombre"],
                    apellido=form.cleaned_data["apellido"],
                    documento=form.cleaned_data["documento"],
                    nombre_usuario=form.cleaned_data["nombre_usuario"],
                    usuario_creacion=usuario_actual.id_usuario,
                    contrasena=make_password(form.cleaned_data["contrasena"])
                )
                usuario_nuevo.save()

                # Asignar roles al usuario nuevo
                roles = form.cleaned_data["roles"]
                for rol in roles:
                    UsuarioRol.objects.create(id_usuario=usuario_nuevo, id_rol=rol)

                messages.success(request, "Usuario creado exitosamente")
                return redirect("usuarios:usuarios")

            except Exception as e:
                messages.error(request, f"Hubo un error en el servidor: {str(e)}")
        else:
            messages.error(request, "Corrige los errores en el formulario.")
    else:
        form = UsuarioForm()

    return render(request, "usuarios/crear_usuario.html", {"form": form})

@login_required(login_url="/authentication/login")
def usuarioUpdateView(request,id_usuario):
    usuario = Usuario.objects.get(id_usuario=id_usuario)
    # Vista para crear usuarios
    if request.method == "POST":
        form = UsuarioForm(request.POST,instance=usuario)
        # Si no se han hecho modificaciones
        if not form.has_changed():
            messages.info(request, "No ha hecho ningun cambio", extra_tags=" ")
            return redirect('usuarios:usuarios')
        if form.is_valid():
            try:
                # Obtener el usuario actual
                usuario_actual = Usuario.objects.get(nombre_usuario=request.user)

                # Crear el nuevo usuario utilizando los datos validados del formulario
                usuario_nuevo = Usuario.objects.create(
                    nombre=form.cleaned_data["nombre"],
                    apellido=form.cleaned_data["apellido"],
                    documento=form.cleaned_data["documento"],
                    nombre_usuario=form.cleaned_data["nombre_usuario"],
                    usuario_creacion=usuario_actual.id_usuario,
                    contrasena=make_password(form.cleaned_data["contrasena"])
                )
                usuario_nuevo.save()

                # Asignar roles al usuario nuevo
                roles = form.cleaned_data["roles"]
                for rol in roles:
                    UsuarioRol.objects.create(id_usuario=usuario_nuevo, id_rol=rol)

                messages.success(request, "Usuario creado exitosamente")
                return redirect("usuarios:usuarios")

            except Exception as e:
                messages.error(request, f"Hubo un error en el servidor: {str(e)}")
        else:
            messages.error(request, "Corrige los errores en el formulario.")
    else:
        form = UsuarioForm()

    return render(request, "usuarios/crear_usuario.html", {"form": form})

@login_required(login_url="/authentication/login")
def crearRol(request):
    if request.method == 'POST':
        form = RolForm(request.POST)
        if form.is_valid():
            rol = Rol.objects.create(descripcion= form.cleaned_data['descripcion'])
            rol.save()
            permisos = form.cleaned_data['permisos']
            for permiso in permisos:
                RolPermiso.objects.create(id_rol = rol, id_permiso = permiso)

            return redirect('usuarios:roles')
    else:
        form = RolForm()

    return render(request,'usuarios/crear_rol.html',{'form':form})

@login_required(login_url="/authentication/login")
def rolReadView(request):
    roles = Rol.objects.all()
    roles_con_permisos = []

    for rol in roles:
        permisos = RolPermiso.objects.filter(id_rol=rol).select_related('id_permiso')
        roles_con_permisos.append({
            'rol': rol,
            'permisos': permisos
        })

    context = {
        'roles_con_permisos': roles_con_permisos
    }
    return render(request, 'usuarios/roles.html', context=context)


@login_required(login_url="/authentication/login")
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

@login_required(login_url="/authentication/login")
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
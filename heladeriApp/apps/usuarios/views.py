from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages
from .forms import *
from .models import *

@login_required(login_url="/authentication/login")
def usuariosReadView(request):

    # Obtener los campos de los usuarios
    usuarios = Usuario.objects.all()
    columnas = ["Usuario","Nombre", "Apellido","Accion"]
    print(f'{usuarios}')
    context = {
        "columnas":columnas,
        "usuarios": usuarios
    }
    return render(request, "usuarios/usuarios.html", context=context)



@login_required(login_url="/authentication/login")
def crearUsuario(request):
    # Vista para crear usuarios
    if request.method == "POST":
        form = UsuarioForm(request.POST)

        if form.is_valid():
            try:
                usuario_actual = Usuario.objects.get(nombre_usuario=request.user)
                nombre = request.POST["nombre"]
                apellido = request.POST["apellido"]
                documento = request.POST["documento"]
                nombre_usuario = request.POST["nombre_usuario"]
                usuario_creacion = usuario_actual.id_usuario
                contrasena = make_password(request.POST["contrasena"])
                '''
                usuario = form.save(commit=False)
                usuario.set_password(form.cleaned_data["contrasena"])
                usuario.save()
                '''
                usuario_nuevo = Usuario.objects.create(
                    nombre = nombre,
                    apellido = apellido,
                    documento = documento,
                    nombre_usuario = nombre_usuario,
                    usuario_creacion = usuario_creacion,
                    contrasena = contrasena
                )
                usuario_nuevo.save()
                roles = form.cleaned_data["roles"]
                for rol in roles:
                    UsuarioRol.objects.create(id_usuario= usuario_nuevo,id_rol = rol)


                messages.success(request, "Usuario creado exitosamente")
                return redirect("usuarios:usuarios")
            except:
                messages.error(request, "Hubo un error en el servidor")
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
    context = {
        'permisos':permisos
    }

    return render(request, 'usuarios/permisos.html', context=context)
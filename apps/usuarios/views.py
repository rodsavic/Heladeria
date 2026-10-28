from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .acceso import GRUPO_ADMIN, admin_required
from .forms import UsuarioForm
from .models import User
from .permisos import agrupar_permisos, permisos_asignables, permisos_ocultos_ids, resumen_por_modulo


@login_required(login_url="/")
@admin_required
def usuariosReadView(request):
    usuarios = User.objects.order_by('username').prefetch_related('groups')
    columnas = ["Usuario", "Nombre", "Apellido", "Rol", "Estado", "Accion"]
    paginator = Paginator(usuarios, 10)
    usuarios_por_pagina = paginator.get_page(request.GET.get('page'))
    context = {
        "columnas": columnas,
        'usuarios_por_pagina': usuarios_por_pagina,
    }
    return render(request, "usuarios/usuarios.html", context=context)


@login_required(login_url="/")
@admin_required
def createUserView(request):
    form = UsuarioForm(request.POST or None, editor=request.user)
    if request.method == 'POST':
        if form.is_valid():
            with transaction.atomic():
                usuario = form.save(commit=False)
                usuario.usuario_creacion = request.user.id
                usuario.save()
                usuario.groups.set(form.cleaned_data['grupos'])
            messages.success(request, f'Usuario {usuario.username} creado exitosamente.')
            return redirect('usuarios:usuarios')
        messages.error(request, 'Revisá los campos marcados en el formulario.')

    return render(request, 'usuarios/usuarios_create.html', {'form': form})


@login_required(login_url="/")
@admin_required
def usuarioUpdateView(request, id):
    usuario = get_object_or_404(User, id=id)
    form = UsuarioForm(request.POST or None, instance=usuario, editor=request.user)
    if request.method == 'POST':
        if form.is_valid():
            cambio_password = bool(form.cleaned_data.get('password'))
            with transaction.atomic():
                usuario = form.save(commit=False)
                usuario.usuario_modificacion = request.user.id
                usuario.fecha_modificacion = timezone.now()
                usuario.save()
                usuario.groups.set(form.cleaned_data['grupos'])
            # Cambiar la propia contrasena invalida la sesion; se renueva para no desloguear.
            if cambio_password and usuario.pk == request.user.pk:
                update_session_auth_hash(request, usuario)
            messages.success(request, f'Usuario {usuario.username} actualizado exitosamente.')
            return redirect('usuarios:usuarios')
        messages.error(request, 'Revisá los campos marcados en el formulario.')

    return render(request, "usuarios/usuarios_modificar.html", {'form': form, 'usuario': usuario})


@login_required(login_url="/")
@admin_required
@require_POST
def usuarioCambiarEstadoView(request, id):
    usuario = get_object_or_404(User, id=id)
    if usuario.pk == request.user.pk:
        messages.error(request, 'No podés desactivar tu propio usuario.')
        return redirect('usuarios:usuarios')

    usuario.is_active = not usuario.is_active
    usuario.usuario_modificacion = request.user.id
    usuario.fecha_modificacion = timezone.now()
    usuario.save(update_fields=['is_active', 'usuario_modificacion', 'fecha_modificacion'])
    estado = 'activado' if usuario.is_active else 'desactivado'
    messages.success(request, f'Usuario {usuario.username} {estado}.')
    return redirect('usuarios:usuarios')


def _guardar_rol(request, rol, template):
    """Valida y guarda nombre y permisos del rol. Si hay un error vuelve a
    mostrar el formulario con lo que el usuario ya habia marcado."""
    nombre = request.POST.get('name', '').strip()
    permisos_ids = {
        int(permiso_id) for permiso_id in request.POST.getlist('permissions') if permiso_id.isdigit()
    }

    error = None
    if not nombre:
        error = 'El nombre del rol no puede estar vacío.'
    elif rol.pk and rol.name == GRUPO_ADMIN and nombre != GRUPO_ADMIN:
        # El acceso a la administracion depende de este nombre exacto.
        error = f'El rol {GRUPO_ADMIN} no se puede renombrar.'
    elif Group.objects.filter(name__iexact=nombre).exclude(pk=rol.pk).exists():
        error = f'Ya existe un rol con el nombre "{nombre}".'

    if error:
        messages.error(request, error)
        context = {
            'rol': rol,
            'nombre': nombre,
            'modulos': agrupar_permisos(permisos_ids),
        }
        return render(request, template, context)

    # Solo se aceptan permisos de la pantalla; los ocultos que ya tenia el rol se conservan.
    asignables = {permiso.id for permiso in permisos_asignables()}
    ocultos = permisos_ocultos_ids(rol) if rol.pk else []
    es_nuevo = rol.pk is None

    with transaction.atomic():
        rol.name = nombre
        rol.save()
        rol.permissions.set((permisos_ids & asignables) | set(ocultos))

    accion = 'creado' if es_nuevo else 'actualizado'
    messages.success(request, f'El rol "{rol.name}" fue {accion} correctamente.')
    return redirect('usuarios:roles')


@login_required(login_url="/")
@admin_required
def crearRol(request):
    rol = Group()
    if request.method == 'POST':
        return _guardar_rol(request, rol, 'usuarios/crear_rol.html')

    context = {
        'rol': rol,
        'nombre': '',
        'modulos': agrupar_permisos(),
    }
    return render(request, 'usuarios/crear_rol.html', context)


@login_required(login_url="/")
@admin_required
def rolReadView(request):
    roles = Group.objects.order_by('name').prefetch_related('permissions__content_type')
    for rol in roles:
        rol.resumen_permisos = resumen_por_modulo(rol.permissions.all())

    context = {
        'roles': roles
    }
    return render(request, 'usuarios/roles.html', context=context)


@login_required(login_url="/")
@admin_required
def editarRolView(request, id):
    rol = get_object_or_404(Group, id=id)
    if request.method == 'POST':
        return _guardar_rol(request, rol, 'usuarios/editar_rol.html')

    context = {
        'rol': rol,
        'nombre': rol.name,
        'modulos': agrupar_permisos(rol.permissions.values_list('id', flat=True)),
    }
    return render(request, 'usuarios/editar_rol.html', context)

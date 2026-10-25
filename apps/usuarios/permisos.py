"""Agrupa los permisos de Django por modulo y recurso para la pantalla de roles."""
from django.contrib.auth.models import Permission

# Apps internas de Django y catalogos de datos fijos: no se asignan a roles del negocio.
APPS_OCULTAS = {'admin', 'auth', 'contenttypes', 'sessions', 'catalogos'}

# Modelos heredados o tablas puente que no tienen pantalla propia.
MODELOS_OCULTOS = {
    ('usuarios', 'usuario'),
    ('usuarios', 'rol'),
    ('usuarios', 'permiso'),
    ('usuarios', 'usuariorol'),
    ('usuarios', 'rolpermiso'),
}

NOMBRES_MODULO = {
    'ventas': 'Ventas',
    'clientes': 'Clientes',
    'productos': 'Productos',
    'inventario': 'Inventario',
    'proveedores': 'Proveedores',
    'gastos': 'Gastos',
    'factura': 'Facturación',
    'alquileres': 'Alquileres',
    'tipo_pago': 'Tipos de pago',
    'configuracion': 'Configuración',
    'usuarios': 'Usuarios',
}

NOMBRES_RECURSO = {
    ('usuarios', 'user'): 'Usuarios',
}

ACCIONES = (
    ('view', 'Ver'),
    ('add', 'Crear'),
    ('change', 'Editar'),
    ('delete', 'Eliminar'),
)


def _es_visible(permiso):
    ct = permiso.content_type
    return ct.app_label not in APPS_OCULTAS and (ct.app_label, ct.model) not in MODELOS_OCULTOS


def permisos_asignables():
    """Permisos que se muestran en la pantalla de roles."""
    permisos = Permission.objects.select_related('content_type')
    return [p for p in permisos if _es_visible(p)]


def agrupar_permisos(seleccionados=()):
    """Devuelve los modulos con sus recursos y, por recurso, el permiso de cada
    accion CRUD mas los permisos personalizados del modelo."""
    seleccionados = set(seleccionados)
    modulos = {}

    for permiso in permisos_asignables():
        ct = permiso.content_type
        modulo = modulos.setdefault(ct.app_label, {
            'app_label': ct.app_label,
            'nombre': NOMBRES_MODULO.get(ct.app_label, ct.app_label.replace('_', ' ').capitalize()),
            'recursos': {},
        })
        modelo = ct.model_class()
        nombre_recurso = NOMBRES_RECURSO.get((ct.app_label, ct.model)) or (
            str(modelo._meta.verbose_name_plural).capitalize() if modelo else ct.model
        )
        recurso = modulo['recursos'].setdefault(ct.model, {
            'nombre': nombre_recurso,
            'acciones': {accion: None for accion, _ in ACCIONES},
            'extras': [],
        })

        item = {'id': permiso.id, 'nombre': permiso.name, 'checked': permiso.id in seleccionados}
        accion = permiso.codename.split('_', 1)[0]
        if accion in recurso['acciones'] and permiso.codename == f'{accion}_{ct.model}':
            recurso['acciones'][accion] = item
        else:
            recurso['extras'].append(item)

    resultado = []
    for modulo in sorted(modulos.values(), key=lambda m: m['nombre']):
        recursos = sorted(modulo['recursos'].values(), key=lambda r: r['nombre'])
        for recurso in recursos:
            recurso['acciones'] = [recurso['acciones'][accion] for accion, _ in ACCIONES]
        items = [i for r in recursos for i in r['acciones'] + r['extras'] if i]
        resultado.append({
            'app_label': modulo['app_label'],
            'nombre': modulo['nombre'],
            'recursos': recursos,
            'total': len(items),
            'seleccionados': sum(1 for i in items if i['checked']),
        })
    return resultado


def resumen_por_modulo(permisos):
    """Cuenta cuantos permisos visibles tiene un rol en cada modulo."""
    conteo = {}
    for permiso in permisos:
        if not _es_visible(permiso):
            continue
        app_label = permiso.content_type.app_label
        nombre = NOMBRES_MODULO.get(app_label, app_label.replace('_', ' ').capitalize())
        conteo[nombre] = conteo.get(nombre, 0) + 1
    return sorted(conteo.items())


def permisos_ocultos_ids(rol):
    """Permisos que el rol ya tiene pero no se muestran: se conservan al guardar."""
    return [p.id for p in rol.permissions.select_related('content_type') if not _es_visible(p)]

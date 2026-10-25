"""Regla unica de acceso a la administracion: pertenecer al grupo ADMIN."""
from django.contrib.auth.decorators import user_passes_test

GRUPO_ADMIN = 'ADMIN'


def es_admin(user):
    return user.is_authenticated and user.groups.filter(name=GRUPO_ADMIN).exists()


admin_required = user_passes_test(es_admin, login_url='/')

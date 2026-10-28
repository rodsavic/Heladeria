"""Proteccion en el servidor contra el doble envio de formularios de alta.

Uso:
    - En el template, dentro del <form>: {% load custom_filters %}{% token_envio %}
    - En la vista: @envio_unico('app:lista')

Cada vez que se renderiza el formulario se genera un token nuevo. Al recibir el
POST se registra el token; si ya estaba registrado el envio es un duplicado y
se redirige sin procesarlo.
"""
import uuid
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.utils import timezone

from apps.models import EnvioFormulario

CAMPO_TOKEN = 'token_envio'
# Pasado este plazo un token ya no puede repetirse en la practica y se borra.
RETENCION = timedelta(days=2)


def nuevo_token():
    return uuid.uuid4().hex


def registrar_token(token):
    """Devuelve True si el token es nuevo, False si ya se habia usado."""
    try:
        with transaction.atomic():
            EnvioFormulario.objects.create(token=token)
    except IntegrityError:
        return False
    EnvioFormulario.objects.filter(fecha__lt=timezone.now() - RETENCION).delete()
    return True


def envio_unico(redirigir_a):
    """Descarta el POST si su token ya se proceso. Un POST sin token (pagina
    cacheada de antes de este cambio) se procesa como siempre."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            token = request.POST.get(CAMPO_TOKEN, '')[:64] if request.method == 'POST' else ''
            if token and not registrar_token(token):
                messages.warning(
                    request,
                    'Este formulario ya fue enviado. Revisá el listado antes de cargarlo de nuevo.',
                )
                return redirect(redirigir_a)
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador

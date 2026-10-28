from decimal import Decimal
from django import template
from django.utils.html import format_html

from apps.envio_unico import CAMPO_TOKEN, nuevo_token
from apps.usuarios.acceso import es_admin as _es_admin

register = template.Library()


@register.simple_tag
def token_envio():
    """Campo oculto con un token nuevo para @envio_unico."""
    return format_html('<input type="hidden" name="{}" value="{}">', CAMPO_TOKEN, nuevo_token())


@register.filter
def es_admin(user):
    return _es_admin(user)

@register.filter(name='add_class')
def add_class(value, arg):
    return value.as_widget(attrs={'class': arg})

@register.filter
def punto_comma(value):
    value = Decimal(value)
    return f"{value:,.0f}".replace(",", ".")

@register.filter
def elided_page_range(paginator, number):
    return paginator.get_elided_page_range(number, on_each_side=1, on_ends=1)
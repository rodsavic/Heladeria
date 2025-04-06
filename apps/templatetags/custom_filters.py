from decimal import Decimal
from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    return value.as_widget(attrs={'class': arg})

@register.filter
def punto_comma(value):
    value = Decimal(value)
    return f"{value:,.0f}".replace(",", ".")
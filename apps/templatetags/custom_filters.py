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

@register.filter
def elided_page_range(paginator, number):
    return paginator.get_elided_page_range(number, on_each_side=1, on_ends=1)
from django import forms
from .models import *


class ProductosForm(forms.ModelForm):
    iva = forms.ModelChoiceField (
        queryset=Iva.objects.all(),
        widget=forms.Select,
        required=False
    )
    medida = forms.ModelChoiceField (
        queryset=Medida.objects.all(),
        widget=forms.Select(attrs={
                'class':'form-control'}),
        required=False
    )
    vencimiento = forms.DateField(
        widget=forms.DateInput(
            format='%d-%m-%Y',
            attrs={
                'type': 'date',  
            }
        )
    )
    class Meta:
        model = Producto
        fields = ['nombre','precio_actual', 'stock_minimo', 'stock_actual','vencimiento', 'costo_actual', 'iva','medida']
    
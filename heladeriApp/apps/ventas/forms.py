from django import forms

from heladeriApp.apps.ventas.models import Venta


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['fecha_venta', 'total_iva_10', 'total_iva_5', 'total_venta', 'usuario_creacion', 'id_cliente']
        widgets = {
            'fecha_venta': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'total_iva_10': forms.NumberInput(attrs={'step': '0.01'}),
            'total_iva_5': forms.NumberInput(attrs={'step': '0.01'}),
            'total_venta': forms.NumberInput(attrs={'step': '0.01'}),
            'usuario_creacion': forms.NumberInput(),
            'id_cliente': forms.NumberInput(),
        }

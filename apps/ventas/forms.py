from django import forms

from apps.ventas.models import Venta, VentaDetalle


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['total_iva_10', 'total_iva_5', 'total_venta','id_cliente']
        widgets = {
            'total_iva_10': forms.NumberInput(attrs={'step': '0.01'}),
            'total_iva_5': forms.NumberInput(attrs={'step': '0.01'}),
            'total_venta': forms.NumberInput(attrs={'step': '0.01'}),
            'id_cliente': forms.Select(attrs={'class':'form-control'}),
        }

        
'''
class VentaDetalleForm(forms.ModelForm):
    class Meta:
        model = VentaDetalle
        fields = ['total_detalle', 'cantidad_producto', 'id_producto']
        widgets = {
            'total_detalle': forms.NumberInput(attrs={'step': '0.01', 'readonly': 'readonly', 'class': 'total-detalle'}),
            'cantidad_producto': forms.NumberInput(attrs={'class': 'cantidad-producto', 'min': '1'}),
            'id_producto': forms.Select(attrs={'class':'form-control'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        cantidad = self.cleaned_data.get('cantidad_producto', 0)
        producto = self.cleaned_data.get('id_producto')
        if producto:
            instance.total_detalle = cantidad * producto.costo_actual
        if commit:
            instance.save()
        return instance

            

VentaDetalleFormSet = forms.inlineformset_factory(
    Venta, 
    VentaDetalle, 
    fields=('total_detalle', 'cantidad_producto', 'id_producto'), 
    extra=1
    )
'''
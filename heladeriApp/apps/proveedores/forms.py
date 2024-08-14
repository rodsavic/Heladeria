from django import forms

from apps.proveedores.models import Proveedor

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['documento', 'nombre', 'telefono', 'direccion', 'correo']

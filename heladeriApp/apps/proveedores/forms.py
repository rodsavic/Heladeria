from django.forms import TextInput,ModelForm, ValidationError
from apps.proveedores.models import Proveedor

class ProveedorForm(ModelForm):
    class Meta:
        model = Proveedor
        exclude = ['id_proveedor','estado','usuario_creacion','usuario_modificacion','fecha_creacion','fecha_modificacion']
        widgets = {
            'nombre': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Nombre'
            }),
            'documento': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Documento'
            }),
            'correo': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Correo'
            }),
            'telefono': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Celular'
            }),
            'direccion': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Direccion'
            }),
        }
        #fields = ['nombre', 'documento', 'apellido','celular','correo','direccion']

    def clean_nombre(self):
        """
        Validamos que el documento del proveedor a crear
        no se encuentre en uso
        """
        documento = self.cleaned_data['documento']

        instance = self.instance
        queryset = Proveedor.objects.filter(documento=documento).exclude(id_proveedor=instance.id_proveedor)
        
        if queryset.exists():
            raise ValidationError('El nombre ya existe!')
        return documento
        #fields = ['documento', 'nombre', 'telefono', 'direccion', 'correo']

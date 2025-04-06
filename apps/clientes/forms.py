from django.forms import ModelForm, TextInput,ValidationError
from .models import *

class ClienteForm(ModelForm):
    class Meta:
        model = Cliente
        exclude = ['id_cliente','estado']
        widgets = {
            'nombre': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Nombre'
            }),
            'apellido': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Apellido'
            }),
            'documento': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Documento'
            }),
            'correo': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Correo'
            }),
            'celular': TextInput(attrs={
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
        Validamos que el nombre del cliente a crear
        no se encuentre en uso
        """
        nombre = self.cleaned_data['nombre']

        instance = self.instance
        queryset = Cliente.objects.filter(nombre=nombre).exclude(id_cliente=instance.id_cliente)
        
        if queryset.exists():
            raise ValidationError('El nombre ya existe!')
        return nombre
from django.forms import CharField, CheckboxSelectMultiple, ModelForm, ModelMultipleChoiceField, PasswordInput, SelectMultiple, TextInput
from apps.usuarios.models import *
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group, Permission

from django import forms


class UsuarioForm(ModelForm):
    contrasena = CharField(
        widget=PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        label="Contraseña"
    )
    contrasena2 = CharField(
        widget=PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirma la contraseña'
        }),
        label="Confirma la contraseña"
    )
    
    roles = ModelMultipleChoiceField(
        queryset=Rol.objects.all(),
        widget=SelectMultiple(attrs={
            'class': 'form-control',
            'placeholder': 'Selecciona uno o más roles'
        }),
        required=False
    )

    class Meta:
        model = Usuario
        exclude = ['id_usuario', 'estado','usuario_creacion','usuario_modificacion','fecha_creacion','fecha_modificacion']
        widgets = {
            'nombre_usuario': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de usuario'
            }),
            'nombre': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'apellido': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
            'documento': TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Documento'
            }),
        }

    def clean_nombre_usuario(self):
        """
        Validamos que el nombre de usuario no esté duplicado
        """
        nombre_usuario = self.cleaned_data['nombre_usuario']
        instance = self.instance

        queryset = Usuario.objects.filter(nombre_usuario=nombre_usuario).exclude(id_usuario=instance.id_usuario)
        
        if queryset.exists():
            raise ValidationError('El nombre de usuario ya existe!')
        return nombre_usuario

    def clean_documento(self):
        """
        Validamos que el documento no esté duplicado
        """
        documento = self.cleaned_data['documento']
        instance = self.instance

        queryset = Usuario.objects.filter(documento=documento).exclude(id_usuario=instance.id_usuario)
        
        if queryset.exists():
            raise ValidationError('El documento ya existe!')
        return documento

    def clean(self):
        """
        Validamos que las contraseñas coincidan
        """
        cleaned_data = super().clean()
        contrasena = cleaned_data.get("contrasena")
        contrasena2 = cleaned_data.get("contrasena2")

        if contrasena and contrasena2 and contrasena != contrasena2:
            raise ValidationError("Las contraseñas no coinciden.")

        return cleaned_data


class PermisoForm(ModelForm):
    class Meta:
        model = Permiso
        fields = ['descripcion']


class RolForm(ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-control',
            'placeholder': 'Selecciona uno o más permisos'
        }),
        required=False
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']



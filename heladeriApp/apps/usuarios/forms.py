from django import forms
from apps.usuarios.models import *


class UsuarioForm(forms.ModelForm):
    contrasena = forms.CharField(widget=forms.PasswordInput(), label="Contraseña")
    contrasena2 = forms.CharField(widget=forms.PasswordInput(), label="Confirma la contraseña")
    roles = forms.ModelMultipleChoiceField(
        queryset=Rol.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Usuario
        fields = ["nombre_usuario", "nombre", "apellido", "documento","contrasena","roles"]

    def clean(self):
        cleaned_data = super().clean()
        contrasena = cleaned_data.get("contrasena")
        contrasena2 = cleaned_data.get("contrasena2")

        if contrasena and contrasena2 and contrasena != contrasena2:
            self.add_error('contrasena2', "Las contraseñas no coinciden.")

        return cleaned_data


class PermisoForm(forms.ModelForm):
    class Meta:
        model = Permiso
        fields = ['descripcion']


class RolForm(forms.ModelForm):
    permisos = forms.ModelMultipleChoiceField(
        queryset=Permiso.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Rol
        fields = ['descripcion', 'permisos']


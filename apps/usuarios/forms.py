from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.usuarios.acceso import GRUPO_ADMIN
from apps.usuarios.models import User


class UsuarioForm(forms.ModelForm):
    """Alta y edicion de usuarios. La contrasena es obligatoria solo al crear."""
    password = forms.CharField(
        label='Contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}))
    password_repetir = forms.CharField(
        label='Repetir contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}))
    grupos = forms.ModelMultipleChoiceField(
        label='Rol', queryset=Group.objects.order_by('name'), required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'telefono', 'cargo', 'direccion', 'fecha_nacimiento']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'username': 'Username',
            'email': 'Correo',
            'telefono': 'Teléfono',
            'cargo': 'Cargo',
            'direccion': 'Dirección',
            'fecha_nacimiento': 'Fecha de nacimiento',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, editor=None, **kwargs):
        # editor: usuario logueado, para que no se quite a si mismo el rol ADMIN.
        self.editor = editor
        super().__init__(*args, **kwargs)
        self.es_alta = self.instance.pk is None
        self.fields['first_name'].required = True
        self.fields['password'].required = self.es_alta
        self.fields['password_repetir'].required = self.es_alta
        if not self.es_alta:
            self.fields['password'].help_text = 'Dejar vacío para mantener la contraseña actual.'
            self.initial['grupos'] = list(self.instance.groups.values_list('pk', flat=True))

    def full_clean(self):
        super().full_clean()
        for nombre in self.errors:
            if nombre in self.fields:
                widget = self.fields[nombre].widget
                widget.attrs['class'] = f"{widget.attrs.get('class', '')} is-invalid".strip()

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Ya existe un usuario con ese username.')
        return username

    def clean_grupos(self):
        grupos = self.cleaned_data['grupos']
        es_el_mismo = self.editor is not None and self.editor.pk == self.instance.pk
        if es_el_mismo and not any(g.name == GRUPO_ADMIN for g in grupos):
            raise ValidationError(f'No podés quitarte a vos mismo el rol {GRUPO_ADMIN}.')
        return grupos

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_repetir = cleaned_data.get('password_repetir')

        if password or password_repetir:
            if password != password_repetir:
                self.add_error('password_repetir', 'Las contraseñas no coinciden.')
            else:
                # Se valida contra los datos nuevos para detectar contrasenas parecidas al nombre o username.
                candidato = User(
                    username=cleaned_data.get('username', ''),
                    first_name=cleaned_data.get('first_name', ''),
                    last_name=cleaned_data.get('last_name', ''),
                    email=cleaned_data.get('email', ''),
                )
                try:
                    validate_password(password, candidato)
                except ValidationError as error:
                    self.add_error('password', error)
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('password'):
            usuario.set_password(self.cleaned_data['password'])
        if commit:
            usuario.save()
            usuario.groups.set(self.cleaned_data['grupos'])
        return usuario

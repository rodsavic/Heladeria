from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Nombre de usuario', max_length=254)
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)

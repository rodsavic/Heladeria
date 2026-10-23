from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.core.cache import cache

MAX_INTENTOS_LOGIN = 5
BLOQUEO_LOGIN_SEGUNDOS = 15 * 60

'''
def crearUsuario(request):
    if request.method == 'GET':
        form = UserCreationForm
        return render(request, 'authentication/signup.html', {"form": form})
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(username=request.POST['username'],password=request.POST['password'])
            except:
                return HttpResponse('Username already exist')
        else:
            return HttpResponse('Password do not match')
            
'''
def _clave_intentos_login(request):
    # Se cuenta por nombre de usuario: detrás del proxy de Railway la IP de
    # origen no es confiable (X-Forwarded-For lo puede falsificar el cliente).
    username = request.POST.get('username', '').strip().lower()
    return f'login_fallidos:{username}'


def login_view(request):
    if request.method == "POST":
        clave = _clave_intentos_login(request)
        if cache.get(clave, 0) >= MAX_INTENTOS_LOGIN:
            messages.error(request, "Demasiados intentos fallidos. Intente de nuevo en 15 minutos.")
            return render(request, 'authentication/login.html', {'form': AuthenticationForm()}, status=429)

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            cache.delete(clave)
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, "Has iniciado sesión exitosamente.")
            return redirect('home:index')
        else:
            cache.set(clave, cache.get(clave, 0) + 1, BLOQUEO_LOGIN_SEGUNDOS)
            messages.error(request, "Nombre de usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'authentication/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, "Has cerrado sesión exitosamente.")
    return redirect('authentication:login')
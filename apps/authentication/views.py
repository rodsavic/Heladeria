from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages

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
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, "Has iniciado sesión exitosamente.")
            return redirect('dashboard:dashboard')
        else:
            messages.error(request, "Nombre de usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'authentication/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, "Has cerrado sesión exitosamente.")
    return redirect('authentication:login')
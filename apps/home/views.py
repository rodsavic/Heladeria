from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

#from apps.usuarios.models import Usuario

@login_required(login_url="/authentication/login")
def home(request):
    usuario_actual = request.user
    print(f'Usuario Actual: {usuario_actual.id}')
    context = {
        "usuario_actual": usuario_actual,
    }
    return render(request,"home/index.html",context=context)
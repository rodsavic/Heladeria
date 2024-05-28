from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
def usuarios(request):
    return HttpResponse('USUARIOS')
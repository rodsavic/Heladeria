from django.urls import path
from . import views

app_name = 'productos'

urlpatterns = [
    path('',views.productosReadView, name='productos'),
    path('crear_producto/', views.createProductosView, name='crear_producto')
]

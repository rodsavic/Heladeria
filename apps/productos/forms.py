from django.forms import ModelForm, TextInput, NumberInput, Select, DateInput, ModelChoiceField, DateField,ValidationError
from .models import *


class ProductosForm(ModelForm):
    '''
    iva = ModelChoiceField (
        queryset=Iva.objects.all(),
        widget=Select,
        required=False
    )
    medida = ModelChoiceField (
        queryset=Medida.objects.all(),
        widget=Select(attrs={
                'class':'form-control'}),
        required=False
    )
    vencimiento = DateField(
        widget=DateInput(
            format='%d-%m-%Y',
            attrs={
                'type': 'date',  
            }
        )
    )'''
    class Meta:
        model = Producto
        labels = {
            'id_iva':'IVA',
            'id_medida': "Medida",
        }
        exclude = ['id_producto','usuario_creacion','usuario_modificacion','fecha_modificacion']
        widgets = {
            'nombre': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Ingrese el nombre del producto',
                'aria-label': 'Nombre de producto'
            }),
            'precio_actual':NumberInput(attrs={
                'class':'form-control',
                'placeholder': 'Ingrese el precio actual',
                'min':1,
                'aria-label': 'Precio actual'
            }),
            'precio_pedidos_ya':NumberInput(attrs={
                'class':'form-control',
                'placeholder': 'Ingrese el precio para Pedidos Ya',
                'min':1,
                'aria-label': 'Precio Pedidos Ya'
            }),
            'costo_actual': NumberInput(attrs={
                'class':'form-control',
                'placeholder': 'Ingrese el costo actual',
                'min':1
            }),
            'vencimiento': TextInput(attrs={
                'class':'form-control',
                'type': 'date', 
                'pattern': '\\d{2}/\\d{2}/\\d{4}', 
                'title': 'Ingrese la fecha con el siguiente formato DD/MM/YYYY'
            }),
            'stock_actual': NumberInput(attrs={
                'class':'form-control',
                'placeholder': 'Ingrese el stock actual',
                'min':0
            }),
            'stock_minimo': NumberInput(attrs={
                'class':'form-control',
                'placeholder': 'Ingrese el stock minimo',
                'min':0
            }),
            'id_iva': Select(attrs={
                'class':'form-control',}),
            'id_medida': Select(attrs={
                'class':'form-control'}),
        }
        #fields = ['nombre','precio_actual', 'stock_minimo', 'stock_actual','vencimiento', 'costo_actual', 'iva','medida']
    
    def clean_nombre(self):
        """
        Validamos que el nombre del producto a crear
        no se encuentre en uso
        """
        nombre = self.cleaned_data['nombre']

        instance = self.instance
        queryset = Producto.objects.filter(nombre=nombre).exclude(id_producto=instance.id_producto)
        
        if queryset.exists():
            raise ValidationError('El nombre ya existe!')
        return nombre

    def clean(self):
        cleaned_data = super().clean()
        precio_actual = cleaned_data.get('precio_actual')
        precio_pedidos_ya = cleaned_data.get('precio_pedidos_ya')

        if precio_actual is not None and (precio_pedidos_ya is None or float(precio_pedidos_ya) <= 0):
            cleaned_data['precio_pedidos_ya'] = float(precio_actual) * 1.30

        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_iva'].empty_label = 'Seleccione un IVA'
        self.fields['id_medida'].empty_label = 'Seleccione una medida'

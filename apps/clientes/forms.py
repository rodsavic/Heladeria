from django import forms
from django.forms import ModelForm, TextInput,ValidationError
from apps.catalogos.models import Ciudad, Departamento, Distrito
from .models import *

class ClienteForm(ModelForm):
    # Campos auxiliares para elegir la ciudad en cascada (departamento -> distrito -> ciudad)
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.all(), required=False, empty_label='Seleccione...',
        widget=forms.Select(attrs={'class': 'form-select'}))
    distrito = forms.ModelChoiceField(
        queryset=Distrito.objects.none(), required=False, empty_label='Seleccione...',
        widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = Cliente
        exclude = ['id_cliente','estado','tipo_operacion']
        widgets = {
            'nombre': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Nombre'
            }),
            'apellido': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Apellido'
            }),
            'documento': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Documento'
            }),
            'correo': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Correo'
            }),
            'celular': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Celular'
            }),
            'direccion': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Direccion'
            }),
            'nombre_fantasia': TextInput(attrs={
                'class':'form-control',
                'placeholder': 'Nombre de fantasía (opcional)'
            }),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_casa': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'id_ciudad': forms.Select(attrs={'class': 'form-select'}),
            'pais': forms.Select(attrs={'class': 'form-select'}),
            'es_proveedor_estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_contribuyente': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_persona_juridica': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'id_ciudad': 'Ciudad',
            'pais': 'País',
        }
        #fields = ['nombre', 'documento', 'apellido','celular','correo','direccion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Los formularios que no envian estos campos (ej. alta rapida en ventas) usan los valores por defecto
        self.fields['tipo_documento'].required = False
        self.fields['numero_casa'].required = False
        self.fields['id_ciudad'].empty_label = 'Seleccione...'
        self.fields['pais'].empty_label = 'Seleccione...'

        # Distritos y ciudades: solo los del departamento/distrito elegido (o del cliente que se edita)
        departamento_id = distrito_id = None
        if self.is_bound:
            departamento_id = self.data.get('departamento') or None
            distrito_id = self.data.get('distrito') or None
        elif self.instance.pk and self.instance.id_ciudad_id:
            ciudad = self.instance.id_ciudad
            distrito_id = ciudad.distrito_id
            departamento_id = ciudad.distrito.departamento_id
            self.initial['distrito'] = distrito_id
            self.initial['departamento'] = departamento_id
        if departamento_id:
            self.fields['distrito'].queryset = Distrito.objects.filter(departamento_id=departamento_id)
        if distrito_id:
            self.fields['id_ciudad'].queryset = Ciudad.objects.filter(distrito_id=distrito_id)
        else:
            self.fields['id_ciudad'].queryset = Ciudad.objects.none()

    def clean_tipo_documento(self):
        return self.cleaned_data.get('tipo_documento') or Cliente.TIPO_DOC_CEDULA_PARAGUAYA

    def clean_numero_casa(self):
        return self.cleaned_data.get('numero_casa') or 0

    def clean_nombre(self):
        """
        Validamos que el nombre del cliente a crear
        no se encuentre en uso
        """
        nombre = self.cleaned_data['nombre']

        instance = self.instance
        queryset = Cliente.objects.filter(nombre=nombre).exclude(id_cliente=instance.id_cliente)
        
        if queryset.exists():
            raise ValidationError('El nombre ya existe!')
        return nombre
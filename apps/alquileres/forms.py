from django import forms
from django.forms import (
    CheckboxInput,
    DateInput,
    ModelForm,
    NumberInput,
    Select,
    Textarea,
    TextInput,
    inlineformset_factory,
)

from apps.clientes.models import Cliente

from .models import ConceptoContrato, Contrato

AYUDA_VARIABLES = "Puedes usar {periodo}, {mes} y {anio}: se reemplazan al facturar."


class ClienteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, cliente):
        return f"{cliente.nombre} {cliente.apellido} - {cliente.documento}".strip()


class ContratoForm(ModelForm):
    id_cliente = ClienteChoiceField(
        queryset=Cliente.objects.order_by("nombre", "apellido"),
        label="Cliente",
        widget=Select(attrs={"class": "form-select"}),
    )
    fecha_inicio = forms.DateField(
        input_formats=["%Y-%m-%d"],
        widget=DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
    )
    fecha_fin = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
    )

    class Meta:
        model = Contrato
        fields = [
            "id_cliente",
            "descripcion",
            "periodicidad",
            "fecha_inicio",
            "fecha_fin",
            "observacion",
            "activo",
        ]
        widgets = {
            "descripcion": TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. Local 3 - Galería Central",
                    "maxlength": 120,
                }
            ),
            "periodicidad": Select(attrs={"class": "form-select"}),
            "observacion": Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Garantías asociadas, condiciones del contrato, etc. Se imprime en la factura.",
                }
            ),
            "activo": CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "descripcion": "Descripción",
            "observacion": "Observación de la factura",
        }
        help_texts = {
            "observacion": AYUDA_VARIABLES,
        }

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("fecha_inicio")
        fin = cleaned_data.get("fecha_fin")
        if inicio and fin and fin < inicio:
            self.add_error("fecha_fin", "La fecha de fin no puede ser anterior a la de inicio.")
        return cleaned_data


class ConceptoContratoForm(ModelForm):
    class Meta:
        model = ConceptoContrato
        fields = ["tipo", "descripcion", "observacion", "monto", "iva", "cobro_unico"]
        widgets = {
            "tipo": Select(attrs={"class": "form-select"}),
            "descripcion": TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. Alquiler Local 3 - {periodo}",
                    "maxlength": 120,
                }
            ),
            "observacion": Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descripción larga del concepto (opcional)",
                }
            ),
            "monto": NumberInput(attrs={"class": "form-control", "min": "1", "step": "1"}),
            "iva": Select(attrs={"class": "form-select"}),
            "cobro_unico": CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "descripcion": "Descripción (máx. 120)",
            "observacion": "Detalle",
            "monto": "Monto (Gs., IVA incluido)",
            "cobro_unico": "Cobrar solo en la primera factura",
        }

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if monto is not None and monto <= 0:
            raise forms.ValidationError("El monto debe ser mayor a cero.")
        return monto


ConceptoFormSet = inlineformset_factory(
    Contrato,
    ConceptoContrato,
    form=ConceptoContratoForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)

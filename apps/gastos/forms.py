from django import forms
from django.forms import DateInput, ModelForm, NumberInput, Select, TextInput
from django.utils import timezone

from .models import Gasto


class GastoForm(ModelForm):
    fecha = forms.DateField(
        input_formats=["%Y-%m-%d"],
        widget=DateInput(
            format="%Y-%m-%d",
            attrs={
                "class": "form-control",
                "type": "date",
            },
        ),
    )

    class Meta:
        model = Gasto
        exclude = [
            "id_gasto",
            "usuario_creacion",
            "usuario_modificacion",
            "fecha_creacion",
            "fecha_modificacion",
        ]
        widgets = {
            "descripcion": TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ingrese la descripcion del gasto",
                    "maxlength": 255,
                }
            ),
            "costo": NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ingrese el costo",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "id_tipo_pago": Select(
                attrs={
                    "class": "form-select",
                }
            ),
        }
        labels = {
            "id_tipo_pago": "Forma de pago",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.initial.get("fecha"):
            self.initial["fecha"] = timezone.localdate()
        if not self.instance.pk and not self.is_bound:
            self.fields["fecha"].initial = timezone.localdate()

    def clean_descripcion(self):
        descripcion = self.cleaned_data["descripcion"].strip()
        if not descripcion:
            raise forms.ValidationError("La descripcion es obligatoria.")
        return descripcion

    def clean_costo(self):
        costo = self.cleaned_data["costo"]
        if costo <= 0:
            raise forms.ValidationError("El costo debe ser mayor a cero.")
        return costo


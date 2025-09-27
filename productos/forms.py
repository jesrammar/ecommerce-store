from django import forms
from .models import Variante

class VarianteForm(forms.Form):
    variante = forms.ModelChoiceField(
        queryset=Variante.objects.none(),
        required=False,
        empty_label="Selecciona talla/color",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    def __init__(self, *args, **kwargs):
        producto = kwargs.pop("producto", None)
        super().__init__(*args, **kwargs)
        if producto:
            self.fields["variante"].queryset = producto.variantes.all()

class PersonalizacionForm(forms.Form):
    texto = forms.CharField(label="Texto", required=False, max_length=30,
                            widget=forms.TextInput(attrs={"class": "form-control"}))
    color_texto = forms.CharField(label="Color del texto", required=False, initial="#ffffff",
                                  widget=forms.TextInput(attrs={"class": "form-control", "placeholder":"#000000"}))
    imagen = forms.ImageField(label="Imagen (opcional)", required=False,
                              widget=forms.ClearableFileInput(attrs={"class": "form-control"}))

from django import forms

class DatosEnvioForm(forms.Form):
    email = forms.EmailField()
    nombre = forms.CharField(max_length=120)
    telefono = forms.CharField(max_length=30, required=False)
    direccion = forms.CharField(max_length=200)
    ciudad = forms.CharField(max_length=120)
    cp = forms.CharField(max_length=12)
    aceptar_politica = forms.BooleanField(label="Acepto la política de privacidad")

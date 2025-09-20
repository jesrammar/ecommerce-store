from django import forms
from .models import Pedido

class SeguimientoIDForm(forms.Form):
    pedido_id = forms.IntegerField(label="ID de pedido")
    email = forms.EmailField(label="Email usado en la compra")


class DatosEnvioForm(forms.Form):
    nombre = forms.CharField(max_length=120)
    email = forms.EmailField()
    telefono = forms.CharField(max_length=30, required=False)
    direccion = forms.CharField(max_length=200)
    ciudad = forms.CharField(max_length=120)
    cp = forms.CharField(max_length=12)

class MetodoPagoForm(forms.Form):
    PAGO_CHOICES = (
        ("contrareembolso", "Contrareembolso"),
        ("tarjeta", "Tarjeta"),
    )
    pago_metodo = forms.ChoiceField(
        choices=PAGO_CHOICES,
        widget=forms.RadioSelect,
        initial="contrareembolso",
    )

from django import forms
from .models import ShippingMethod, Pedido

class DatosEnvioForm(forms.Form):
    nombre = forms.CharField(max_length=120, label="Nombre completo")
    email = forms.EmailField(label="Correo electrónico")
    telefono = forms.CharField(max_length=30, label="Teléfono", required=False)
    direccion = forms.CharField(max_length=200, label="Dirección")
    ciudad = forms.CharField(max_length=120, label="Ciudad")
    cp = forms.CharField(max_length=12, label="Código postal")
    envio_metodo = forms.ModelChoiceField(
        queryset=ShippingMethod.objects.filter(activo=True).order_by("orden", "id"),
        empty_label=None,
        label="Método de entrega",
        widget=forms.RadioSelect,
    )

class MetodoPagoForm(forms.Form):
    # Si en tu modelo Pedido definiste choices, puedes importarlas desde ahí. Por simplicidad:
    PAGO_METODOS = (
        ("contrareembolso", "Contrareembolso"),
        ("tarjeta", "Tarjeta (Stripe)"),
    )
    pago_metodo = forms.ChoiceField(choices=PAGO_METODOS, widget=forms.RadioSelect)

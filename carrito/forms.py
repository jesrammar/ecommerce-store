from django import forms
from pedidos.models import ShippingMethod

class ShippingSelectForm(forms.Form):
    shipping_method = forms.ModelChoiceField(
        queryset=ShippingMethod.objects.filter(activo=True).order_by("orden"),
        widget=forms.RadioSelect,
        empty_label=None,
        label="Forma de entrega",
    )


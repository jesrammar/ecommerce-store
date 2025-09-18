from django import forms
from django.contrib.auth.models import User
from .models import CustomerProfile, Address

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repite la contraseña", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("password2"):
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return data

class PerfilForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ("telefono", "metodo_pago_preferido")

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ("user", "es_predeterminada")

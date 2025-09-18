from django.conf import settings
from django.db import models

class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses")
    nombre = models.CharField(max_length=100, help_text="Nombre y apellidos")
    linea1 = models.CharField(max_length=120, verbose_name="Dirección")
    linea2 = models.CharField(max_length=120, blank=True, default="")
    ciudad = models.CharField(max_length=80)
    provincia = models.CharField(max_length=80)
    cp = models.CharField(max_length=12, verbose_name="Código postal")
    pais = models.CharField(max_length=2, default="ES")

    es_predeterminada = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Dirección"
        verbose_name_plural = "Direcciones"

    def __str__(self):
        return f"{self.nombre} · {self.linea1}, {self.ciudad} ({self.cp})"

class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    telefono = models.CharField(max_length=20, blank=True, default="")
    direccion_envio_pred = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="default_for_users")
    metodo_pago_preferido = models.CharField(
        max_length=20,
        choices=[("contrareembolso", "Contrareembolso"), ("tarjeta", "Tarjeta")],
        default="contrareembolso",
    )

    def __str__(self):
        return f"Perfil {self.user.get_username()}"

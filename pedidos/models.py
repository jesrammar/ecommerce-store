from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string


class ShippingMethod(models.Model):
    nombre = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    coste = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        verbose_name = "Método de entrega"
        verbose_name_plural = "Métodos de entrega"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.coste} €)"


class Pedido(models.Model):
    # ⬇️ NUEVO: vínculo opcional con el usuario logueado
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pedidos",
    )

    email = models.EmailField()
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=120)
    cp = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)

    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pago_estado = models.CharField(max_length=20, default="pendiente")
    pago_metodo = models.CharField(max_length=20, default="contrareembolso")
    pago_ref = models.CharField(max_length=120, blank=True)

    envio_metodo = models.ForeignKey(
        ShippingMethod, null=True, blank=True, on_delete=models.SET_NULL
    )
    envio_coste = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )

    tracking_token = models.CharField(max_length=32, unique=True, editable=False)

    class Meta:
        ordering = ["-created_at", "id"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def save(self, *args, **kwargs):
        if not self.tracking_token:
            self.tracking_token = get_random_string(32)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Pedido #{self.id} - {self.email}"


class PedidoItem(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="items"
    )
    producto_id = models.IntegerField()
    titulo = models.CharField(max_length=160)
    precio_unit = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    variante = models.ForeignKey(
        "productos.Variante", null=True, blank=True, on_delete=models.SET_NULL
    )
    personalizacion = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Línea de pedido"
        verbose_name_plural = "Líneas de pedido"

    def save(self, *args, **kwargs):
        """
        Si no viene subtotal calculado, lo calculamos automáticamente
        como precio_unit * cantidad. Si ya viene con valor (>0),
        respetamos lo que haya.
        """
        if not self.subtotal or self.subtotal == Decimal("0"):
            precio = self.precio_unit or Decimal("0")
            self.subtotal = precio * self.cantidad
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.titulo} x{self.cantidad}"
    
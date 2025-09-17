from django.db import models
from django.utils.crypto import get_random_string

class Pedido(models.Model):
    email = models.EmailField()
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=120)
    cp = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)

    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pago_estado = models.CharField(max_length=20, default="pendiente")
    pago_ref = models.CharField(max_length=120, blank=True)

    tracking_token = models.CharField(max_length=32, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.tracking_token:
            self.tracking_token = get_random_string(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pedido #{self.id} - {self.email}"

class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto_id = models.IntegerField()
    titulo = models.CharField(max_length=160)
    precio_unit = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.titulo} x{self.cantidad}"

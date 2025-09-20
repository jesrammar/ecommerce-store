from django.core.management.base import BaseCommand
from pedidos.models import ShippingMethod
from decimal import Decimal

DATA = [
    {"nombre":"Estándar (48/72h)", "slug":"standard", "coste":Decimal("3.99"), "orden":1, "activo":True},
    {"nombre":"Urgente (24h)", "slug":"express", "coste":Decimal("6.99"), "orden":2, "activo":True},
    {"nombre":"Recogida en tienda", "slug":"pickup", "coste":Decimal("0.00"), "orden":3, "activo":True},
]

class Command(BaseCommand):
    help = "Crea/actualiza métodos de envío básicos"
    def handle(self, *args, **kwargs):
        for d in DATA:
            ShippingMethod.objects.update_or_create(slug=d["slug"], defaults=d)
        self.stdout.write(self.style.SUCCESS("Métodos de envío listos"))

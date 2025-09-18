from django.core.management.base import BaseCommand
from pedidos.models import ShippingMethod

DEFAULTS = [
    {"nombre": "Estándar (48/72h)", "slug": "standard", "coste": 3.99, "orden": 1},
    {"nombre": "Exprés (24h)", "slug": "express", "coste": 7.99, "orden": 2},
]

class Command(BaseCommand):
    help = "Crea métodos de envío por defecto si no existen"

    def handle(self, *args, **kwargs):
        for data in DEFAULTS:
            ShippingMethod.objects.get_or_create(slug=data["slug"], defaults=data)
        self.stdout.write(self.style.SUCCESS("Métodos de envío listos"))

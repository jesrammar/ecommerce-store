from django.core.management.base import BaseCommand
from django.utils.text import slugify
from productos.models import Producto
from django.db import transaction

class Command(BaseCommand):
    help = "Normaliza a ASCII los slugs de productos y garantiza unicidad"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        vistos = set()
        cambios = 0

        for p in Producto.objects.all().order_by("id"):
            base = slugify(p.slug or p.nombre) or f"producto-{p.pk}"
            nuevo = base
            i = 2
            # evita colisiones con otros productos
            while nuevo in vistos or Producto.objects.exclude(pk=p.pk).filter(slug=nuevo).exists():
                nuevo = f"{base}-{i}"
                i += 1

            vistos.add(nuevo)

            if p.slug != nuevo:
                old = p.slug
                p.slug = nuevo
                p.save(update_fields=["slug"])
                cambios += 1
                self.stdout.write(f"  - {old!r} -> {nuevo!r}")

        self.stdout.write(self.style.SUCCESS(f"Slugs normalizados. Cambios: {cambios}"))

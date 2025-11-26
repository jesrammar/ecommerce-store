from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from django.utils.text import slugify

from productos.models import Categoria, Marca, Producto


class Command(BaseCommand):
    help = "Seed oficial de E-Clothify con productos reales del catálogo final (sin imágenes en BD)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Reseteando catálogo E-Clothify..."))

        # 1) Borrar TODOS los productos actuales (adiós 'Gorra urbana' y compañía)
        Producto.objects.all().delete()

        # 2) Categorías
        ropa, _ = Categoria.objects.get_or_create(nombre="Ropa", slug="ropa")
        accesorios, _ = Categoria.objects.get_or_create(nombre="Accesorios", slug="accesorios")

        # 3) Marcas
        generic, _ = Marca.objects.get_or_create(nombre="Genérica", slug="generica")
        retro, _ = Marca.objects.get_or_create(nombre="RetroWave", slug="retrowave")
        profit, _ = Marca.objects.get_or_create(nombre="ProFit", slug="profit")

        # Helper para crear productos SIN tocar campo imagen
        def add_prod(
            nombre,
            precio,
            categoria,
            marca,
            permite=False,
            precio_nombre=0,
            precio_color=0,
            precio_textura=0,
            stock=50,
            descripcion="",
        ):
            slug = slugify(nombre)
            p, created = Producto.objects.update_or_create(
                slug=slug,
                defaults={
                    "nombre": nombre,
                    "precio": Decimal(str(precio)),
                    "categoria": categoria,
                    "marca": marca,
                    "descripcion": descripcion,
                    # NO seteamos p.imagen -> se queda vacío
                    "permite_personalizacion": permite,
                    "precio_personalizacion_nombre": Decimal(str(precio_nombre)),
                    "precio_personalizacion_color": Decimal(str(precio_color)),
                    "precio_personalizacion_textura": Decimal(str(precio_textura)),
                    "stock": stock,
                    "activo": True,
                },
            )
            return created

        creados = 0

        # -------------------------
        # PRODUCTOS REALES
        # -------------------------

        # Camiseta básica
        creados += add_prod(
            "Camiseta básica",
            20.00,
            ropa,
            generic,
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Camiseta básica personalizable.",
        )

        # Camiseta tirantas
        creados += add_prod(
            "Camiseta tirantas",
            20.00,
            ropa,
            profit,
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Camiseta ligera sin mangas.",
        )

        # Sudadera
        creados += add_prod(
            "Sudadera con capucha",
            19.99,
            ropa,
            generic,
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Sudadera cálida unisex.",
        )

        # Gorra (la buena, ÚNICA)
        creados += add_prod(
            "Gorra",
            15.00,
            accesorios,
            retro,
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Gorra básica personalizable.",
        )

        # ⭐ Pantalón personalizable
        creados += add_prod(
            "Pantalón",
            25.00,
            ropa,
            retro,
            permite=True,
            precio_nombre=0,
            precio_color=5,
            precio_textura=5,
            descripcion="Pantalón personalizable: estándar, roto, parche o roto+parche.",
        )

        self.stdout.write(self.style.SUCCESS(f"Productos creados: {creados}"))

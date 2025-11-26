from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from django.utils.text import slugify

from productos.models import Categoria, Marca, Producto


class Command(BaseCommand):
    help = "Seed oficial de E-Clothify con productos reales del catálogo final."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Cargando productos reales E-Clothify..."))

    
        ropa, _ = Categoria.objects.get_or_create(nombre="Ropa", slug="ropa")
        accesorios, _ = Categoria.objects.get_or_create(nombre="Accesorios", slug="accesorios")

        generic, _ = Marca.objects.get_or_create(nombre="Genérica", slug="generica")
        retro, _ = Marca.objects.get_or_create(nombre="RetroWave", slug="retrowave")
        profit, _ = Marca.objects.get_or_create(nombre="ProFit", slug="profit")

        def add_prod(nombre, precio, categoria, marca, imagen,
                     permite=False, precio_nombre=0, precio_color=0,
                     precio_textura=0, stock=50, descripcion=""):

            slug = slugify(nombre)
            p, created = Producto.objects.update_or_create(
                slug=slug,
                defaults={
                    "nombre": nombre,
                    "precio": Decimal(str(precio)),
                    "categoria": categoria,
                    "marca": marca,
                    "descripcion": descripcion,
                    "imagen": imagen,  # static path
                    "permite_personalizacion": permite,
                    "precio_personalizacion_nombre": Decimal(str(precio_nombre)),
                    "precio_personalizacion_color": Decimal(str(precio_color)),
                    "precio_personalizacion_textura": Decimal(str(precio_textura)),
                    "stock": stock,
                    "activo": True,
                }
            )
            return created

        creados = 0

        # -------------------------
        # PRODUCTOS REALES
        # -------------------------

        creados += add_prod(
            "Camiseta básica",
            20.00,
            ropa,
            generic,
            "img/cami.png",
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Camiseta básica personalizable.",
        )

        creados += add_prod(
            "Camiseta tirantas",
            20.00,
            ropa,
            profit,
            "img/tirantas.png",
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Camiseta ligera sin mangas.",
        )

        creados += add_prod(
            "Sudadera con capucha",
            19.99,
            ropa,
            generic,
            "img/sudadera.png",
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Sudadera cálida unisex.",
        )

        creados += add_prod(
            "Gorra",
            15.00,
            accesorios,
            retro,
            "img/gorra.png",
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Gorra básica personalizable.",
        )

        creados += add_prod(
            "Gorra urbana",
            17.00,
            accesorios,
            generic,
            "img/gorrilla.png",
            permite=True,
            precio_nombre=3,
            precio_color=3,
            precio_textura=5,
            descripcion="Gorra estilo urbano.",
        )

       
        creados += add_prod(
            "Pantalón",
            25.00,
            ropa,
            retro,
            "img/pantalon-estandar.png",
            permite=True,
            precio_nombre=0,
            precio_color=5,
            precio_textura=5,
            descripcion="Pantalón personalizable: estándar, roto, parche o roto+parche.",
        )

        self.stdout.write(self.style.SUCCESS(f"Productos creados/actualizados: {creados}"))

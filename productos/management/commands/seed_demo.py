from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from decimal import Decimal

from productos.models import Categoria, Marca, Producto, Variante


class Command(BaseCommand):
    help = "Rellena la tienda con datos de demo: categorías, marcas, productos y variantes."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Sembrando datos de demo para E-Clothify..."))

        categorias_data = [
            ("Camisetas personalizadas", None),
            ("Sudaderas", None),
            ("Gorras", None),
            ("Accesorios", None),
        ]
        

        categorias = {}
        for nombre, padre_nombre in categorias_data:
            slug = slugify(nombre)
            cat, _ = Categoria.objects.get_or_create(
                slug=slug,
                defaults={"nombre": nombre},
            )
            categorias[nombre] = cat

       
        marcas_nombres = [
            "E-Clothify Basics",
            "StreetLine",
            "ProFit",
            "RetroWave",
        ]

        marcas = {}
        for nombre in marcas_nombres:
            slug = slugify(nombre)
            marca, _ = Marca.objects.get_or_create(
                slug=slug,
                defaults={"nombre": nombre},
            )
            marcas[nombre] = marca

       
        productos_data = [
            {
                "nombre": "Camiseta básica unisex",
                "descripcion": "Camiseta de algodón 100% con opción de personalizar texto frontal.",
                "categoria": "Camisetas personalizadas",
                "marca": "E-Clothify Basics",
                "precio": Decimal("12.90"),
                "destacado": True,
                "permite_personalizacion": True,
                "variantes": [
                    {"talla": "S",  "color": "Blanco", "stock": 10, "extra_precio": Decimal("0.00")},
                    {"talla": "M",  "color": "Blanco", "stock": 15, "extra_precio": Decimal("0.00")},
                    {"talla": "L",  "color": "Negro",  "stock": 0,  "extra_precio": Decimal("0.50")},  # agotado
                    {"talla": "XL", "color": "Negro",  "stock": 5,  "extra_precio": Decimal("0.50")},
                ],
            },
            {
                "nombre": "Sudadera premium con capucha",
                "descripcion": "Sudadera gruesa con interior afelpado y posibilidad de bordar iniciales.",
                "categoria": "Sudaderas",
                "marca": "ProFit",
                "precio": Decimal("29.90"),
                "destacado": True,
                "permite_personalizacion": True,
                "variantes": [
                    {"talla": "S",  "color": "Gris jaspeado", "stock": 3,  "extra_precio": Decimal("0.00")},
                    {"talla": "M",  "color": "Gris jaspeado", "stock": 8,  "extra_precio": Decimal("0.00")},
                    {"talla": "L",  "color": "Negro",         "stock": 0,  "extra_precio": Decimal("1.50")},  # agotado
                    {"talla": "XL", "color": "Negro",         "stock": 4,  "extra_precio": Decimal("1.50")},
                ],
            },
            {
                "nombre": "Gorra snapback bordada",
                "descripcion": "Gorra tipo snapback con visera plana y logo personalizable.",
                "categoria": "Gorras",
                "marca": "StreetLine",
                "precio": Decimal("18.00"),
                "destacado": False,
                "permite_personalizacion": True,
                "variantes": [
                    {"talla": "Única", "color": "Negro", "stock": 7, "extra_precio": Decimal("0.00")},
                    {"talla": "Única", "color": "Rojo",  "stock": 0, "extra_precio": Decimal("0.00")},  # agotada
                ],
            },
            {
                "nombre": "Camiseta retro 90s",
                "descripcion": "Estampado retro inspirado en los 90, ideal para nostálgicos.",
                "categoria": "Camisetas personalizadas",
                "marca": "RetroWave",
                "precio": Decimal("19.90"),
                "destacado": True,
                "permite_personalizacion": False,
                "variantes": [
                    {"talla": "M", "color": "Blanco", "stock": 6, "extra_precio": Decimal("0.00")},
                    {"talla": "L", "color": "Blanco", "stock": 2, "extra_precio": Decimal("0.00")},
                ],
            },
            {
                "nombre": "Calcetines deportivos",
                "descripcion": "Pack de 3 pares de calcetines de alto rendimiento.",
                "categoria": "Accesorios",
                "marca": "ProFit",
                "precio": Decimal("9.90"),
                "destacado": False,
                "permite_personalizacion": False,
                "stock_fijo": 25,
                "variantes": [],
            },
            {
                "nombre": "Mochila urbana",
                "descripcion": "Mochila resistente al agua con compartimento para portátil.",
                "categoria": "Accesorios",
                "marca": "StreetLine",
                "precio": Decimal("39.90"),
                "destacado": True,
                "permite_personalizacion": False,
                "stock_fijo": 0,  # agotada
                "variantes": [],
            },
        ]

        creados = 0
        for pdata in productos_data:
            cat = categorias[pdata["categoria"]]
            marca = marcas[pdata["marca"]]
            nombre = pdata["nombre"]
            slug = slugify(nombre)

            producto, creado = Producto.objects.get_or_create(
                slug=slug,
                defaults={
                    "nombre": nombre,
                    "categoria": cat,
                    "marca": marca,
                    "descripcion": pdata["descripcion"],
                    "precio": pdata["precio"],
                    "stock": 0,
                    "activo": True,
                    "destacado": pdata.get("destacado", False),
                    "permite_personalizacion": pdata.get("permite_personalizacion", False),
                },
            )
            if creado:
                creados += 1

          
            producto.variantes.all().delete()

            total_stock = 0

            # Variantes
            for v in pdata.get("variantes", []):
                Variante.objects.create(
                    producto=producto,
                    talla=v["talla"],
                    color=v["color"],
                    stock=v["stock"],
                    extra_precio=v.get("extra_precio", Decimal("0.00")),
                )
                total_stock += v["stock"]

    
            if pdata.get("variantes") == []:
                total_stock = pdata.get("stock_fijo", 0)

            producto.stock = total_stock
            producto.save(update_fields=["stock"])

        self.stdout.write(self.style.SUCCESS(f"Seed completado. Productos nuevos creados: {creados}"))

# productos/management/commands/seed_demo.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps
from django.utils.text import slugify

def has_field(model, name):
    return any(f.name == name for f in model._meta.get_fields())

class Command(BaseCommand):
    help = "Crea datos de demo (categorías, marcas y productos) adaptándose a los campos existentes"

    @transaction.atomic
    def handle(self, *args, **opts):
        Categoria = apps.get_model("productos", "Categoria")
        Producto  = apps.get_model("productos", "Producto")

        # Marca es opcional (no todos los proyectos la tienen)
        Marca = None
        try:
            Marca = apps.get_model("productos", "Marca")
        except LookupError:
            pass

        # ----- Categoria -----
        cat_kwargs = {"nombre": "Ropa"}
        if has_field(Categoria, "slug"):
            cat_kwargs["slug"] = slugify("Ropa")
        if has_field(Categoria, "descripcion"):
            cat_kwargs["descripcion"] = "Ropa personalizada"

        cat, _ = Categoria.objects.get_or_create(
            **{k: v for k, v in cat_kwargs.items() if k in {f.name for f in Categoria._meta.get_fields()}}
        )

        # ----- Marca (si existe el modelo) -----
        marca = None
        if Marca:
            marca_kwargs = {"nombre": "Genérica"}
            if has_field(Marca, "slug"):
                marca_kwargs["slug"] = slugify("Genérica")
            marca, _ = Marca.objects.get_or_create(
                **{k: v for k, v in marca_kwargs.items() if k in {f.name for f in Marca._meta.get_fields()}}
            )

        # ----- Productos -----
        demos = [
            ("Camiseta básica", "Algodón 100%", 9.99, 20),
            ("Sudadera con capucha", "Cómoda y calentita", 19.99, 12),
            ("Gorra personalizada", "Bordado frontal", 12.50, 15),
        ]

        for nombre, desc, precio, stock in demos:
            p_kwargs = {
                "nombre": nombre,
                "precio": precio,
                "stock": stock,
            }

            # Campos opcionales habituales
            if has_field(Producto, "slug"):
                p_kwargs["slug"] = slugify(nombre)
            if has_field(Producto, "descripcion"):
                p_kwargs["descripcion"] = desc
            if has_field(Producto, "categoria"):
                p_kwargs["categoria"] = cat
            if marca and has_field(Producto, "marca"):
                p_kwargs["marca"] = marca
            if has_field(Producto, "disponible"):
                p_kwargs["disponible"] = True
            if has_field(Producto, "activo"):
                p_kwargs["activo"] = True
            if has_field(Producto, "destacado"):
                p_kwargs["destacado"] = False

            # Construye filtros para get_or_create (robusto)
            lookup = {}
            if has_field(Producto, "slug"):
                lookup["slug"] = p_kwargs["slug"]
            else:
                lookup["nombre"] = nombre

            Producto.objects.get_or_create(
                **lookup,
                defaults=p_kwargs
            )

        self.stdout.write(self.style.SUCCESS("Datos de demo creados/adaptados al modelo actual."))

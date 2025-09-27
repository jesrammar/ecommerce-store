from django.db import models
from django.utils.text import slugify
from django.urls import reverse


class Categoria(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    padre = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="hijas"
    )

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        self.slug = slugify(self.slug or self.nombre)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nombre


class Marca(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        self.slug = slugify(self.slug or self.nombre)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="productos"
    )
    marca = models.ForeignKey(
        Marca, on_delete=models.SET_NULL, null=True, blank=True, related_name="productos"
    )
    nombre = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    imagen = models.ImageField(upload_to="productos/", blank=True)  # pon null=True si quieres
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    permite_personalizacion = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["categoria"]),
            models.Index(fields=["marca"]),
            models.Index(fields=["activo"]),
            models.Index(fields=["destacado"]),
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        self.slug = slugify(self.slug or self.nombre)
        super().save(*args, **kwargs)

    @property
    def agotado(self) -> bool:
        return self.stock == 0

    def get_absolute_url(self):
        return reverse("productos:producto_detalle", kwargs={"slug": self.slug})

    def __str__(self) -> str:
        return self.nombre


class Variante(models.Model):
    producto = models.ForeignKey(
        Producto, related_name="variantes", on_delete=models.CASCADE
    )
    talla = models.CharField(max_length=10)      # S, M, L, XL...
    color = models.CharField(max_length=30)      # nombre o #hex
    stock = models.PositiveIntegerField(default=0)
    extra_precio = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        unique_together = ("producto", "talla", "color")
        verbose_name = "Variante"
        verbose_name_plural = "Variantes"
        indexes = [
            models.Index(fields=["producto"]),
            models.Index(fields=["talla"]),
            models.Index(fields=["color"]),
        ]

    def __str__(self):
        return f"{self.producto.nombre} - {self.talla} - {self.color}"

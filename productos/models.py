from decimal import Decimal  # <-- NUEVO

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
    imagen = models.ImageField(
        upload_to="productos/", blank=True
    )  # pon null=True si quieres
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    permite_personalizacion = models.BooleanField(default=False)

    # === NUEVOS CAMPOS: recargos de personalización ===
    precio_personalizacion_nombre = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Recargo por añadir nombre/texto personalizado.",
    )
    precio_personalizacion_color = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Recargo por elegir un color especial para el texto.",
    )
    precio_personalizacion_textura = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Recargo por textura / imagen subida (logo, estampado, etc.).",
    )

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

    def calcular_precio(self, variante=None, personalizacion=None) -> Decimal:
        """
        Devuelve el precio unitario final combinando:
        - precio base del producto
        - extra_precio de la variante (si la hay)
        - recargos por personalización.

        REGLAS:

        PANTALÓN (tipo="pantalon" en meta o categoría con 'pantal'):
          - estilo = 'estandar'      -> sin recargo
          - estilo = 'roto'          -> +precio_personalizacion_color
          - estilo = 'parche'        -> +precio_personalizacion_textura
          - estilo = 'roto-parche'   -> ambos recargos

        RESTO (camisetas, gorras, etc.) cuando permite_personalizacion=True:
          - Texto -> +precio_personalizacion_nombre
          - Color (no blanco/negro) -> +precio_personalizacion_color
          - Textura/imagen (preview_url) -> +precio_personalizacion_textura
        """
        precio = Decimal(self.precio)

        # Extra de la variante (talla/color)
        if variante is not None:
            precio += Decimal(getattr(variante, "extra_precio", 0) or 0)

        pers = personalizacion or {}

        # --- DETECCIÓN PANTALÓN ---
        tipo = str(pers.get("tipo") or "").lower()
        cat_nombre = (self.categoria.nombre if self.categoria else "") or ""
        es_pantalon = (tipo == "pantalon") or ("pantal" in cat_nombre.lower())

        if es_pantalon:
            estilo = str(pers.get("estilo") or "estandar").lower()
            # Usamos estos campos como recargos "roto" y "parche"
            recargo_roto = Decimal(self.precio_personalizacion_color or 0)
            recargo_parche = Decimal(self.precio_personalizacion_textura or 0)

            if estilo in ("roto", "roto-parche"):
                precio += recargo_roto
            if estilo in ("parche", "roto-parche"):
                precio += recargo_parche
            return precio

        # --- RESTO DE PRODUCTOS ---
        if not self.permite_personalizacion:
            return precio

        texto = pers.get("texto") or ""
        color_texto_raw = pers.get("color_texto") or ""
        color_texto = str(color_texto_raw).strip().lower()
        # Usamos preview_url como señal de que se subió imagen/textura
        tiene_textura = bool(pers.get("preview_url"))

        # Recargo por texto
        if texto:
            precio += Decimal(self.precio_personalizacion_nombre)

        # Colores básicos que NO llevan recargo
        colores_basicos = ("", "#ffffff", "#fff", "#000000", "#000")

        # Recargo por color solo si no es blanco/negro básico
        if color_texto not in colores_basicos:
            precio += Decimal(self.precio_personalizacion_color)

        # Recargo por textura / imagen
        if tiene_textura:
            precio += Decimal(self.precio_personalizacion_textura)

        return precio


class Variante(models.Model):
    producto = models.ForeignKey(
        Producto, related_name="variantes", on_delete=models.CASCADE
    )
    talla = models.CharField(max_length=10)  # S, M, L, XL...
    color = models.CharField(max_length=30)  # nombre o #hex
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

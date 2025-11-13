from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Marca, Producto, Variante
from .forms import VarianteForm, PersonalizacionForm
from . import views


# =====================================================
#   MODELOS: Categoria, Marca, Producto, Variante
# =====================================================

class CategoriaMarcaProductoModelTests(TestCase):
    def test_categoria_slug_se_autogenera_desde_nombre(self):
        cat = Categoria.objects.create(nombre="Ropa Hombre")
        self.assertEqual(cat.slug, "ropa-hombre")

    def test_marca_slug_se_autogenera_desde_nombre(self):
        marca = Marca.objects.create(nombre="Mi Marca Guay")
        self.assertEqual(marca.slug, "mi-marca-guay")

    def test_producto_slug_y_get_absolute_url(self):
        cat = Categoria.objects.create(nombre="Camisetas")
        marca = Marca.objects.create(nombre="Marca X")
        prod = Producto.objects.create(
            categoria=cat,
            marca=marca,
            nombre="Camiseta Blanca",
            precio=Decimal("9.99"),
            stock=10,
        )
        # slug generado a partir del nombre
        self.assertEqual(prod.slug, "camiseta-blanca")
        # get_absolute_url usa ese slug
        self.assertEqual(
            prod.get_absolute_url(),
            reverse("productos:producto_detalle", kwargs={"slug": "camiseta-blanca"}),
        )

    def test_producto_agotado_property(self):
        cat = Categoria.objects.create(nombre="Camisetas")
        marca = Marca.objects.create(nombre="Marca X")
        prod_agotado = Producto.objects.create(
            categoria=cat,
            marca=marca,
            nombre="Sin stock",
            precio=Decimal("9.99"),
            stock=0,
        )
        prod_con_stock = Producto.objects.create(
            categoria=cat,
            marca=marca,
            nombre="Con stock",
            precio=Decimal("9.99"),
            stock=5,
        )
        self.assertTrue(prod_agotado.agotado)
        self.assertFalse(prod_con_stock.agotado)


class VarianteModelTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre="Camisetas",
            slug="camisetas",
        )
        self.marca = Marca.objects.create(
            nombre="Marca Test",
            slug="marca-test",
        )
        self.producto = Producto.objects.create(
            categoria=self.categoria,
            marca=self.marca,
            nombre="Camiseta Negra",
            precio=Decimal("19.99"),
            stock=10,
        )

    def test_variante_str(self):
        variante = Variante.objects.create(
            producto=self.producto,
            talla="M",
            color="Negro",
            stock=5,
            extra_precio=Decimal("0.00"),
        )
        self.assertEqual(str(variante), "Camiseta Negra - M - Negro")

    def test_variante_unique_together(self):
        Variante.objects.create(
            producto=self.producto,
            talla="M",
            color="Negro",
            stock=5,
        )
        # Crear otra con mismo (producto, talla, color) debería fallar
        with self.assertRaises(Exception):
            Variante.objects.create(
                producto=self.producto,
                talla="M",
                color="Negro",
                stock=3,
            )


# =====================================================
#   VISTAS: lista_productos y lista_por_categoria
# =====================================================

class ListaProductosViewTests(TestCase):
    def setUp(self):
        self.cat1 = Categoria.objects.create(nombre="Camisetas")
        self.cat2 = Categoria.objects.create(nombre="Gorras")
        self.marca1 = Marca.objects.create(nombre="Marca Uno")
        self.marca2 = Marca.objects.create(nombre="Marca Dos")

        self.prod1 = Producto.objects.create(
            categoria=self.cat1,
            marca=self.marca1,
            nombre="Camiseta Roja",
            descripcion="Camiseta de algodón roja",
            precio=Decimal("10.00"),
            stock=5,
            activo=True,
        )
        self.prod2 = Producto.objects.create(
            categoria=self.cat1,
            marca=self.marca2,
            nombre="Camiseta Azul",
            descripcion="Ideal para verano",
            precio=Decimal("12.00"),
            stock=0,
            activo=True,
        )
        self.prod3 = Producto.objects.create(
            categoria=self.cat2,
            marca=self.marca1,
            nombre="Gorra Negra",
            descripcion="Gorra ajustable",
            precio=Decimal("8.00"),
            stock=10,
            activo=True,
        )
        # Inactivo, no debería salir
        self.prod_inactivo = Producto.objects.create(
            categoria=self.cat2,
            marca=self.marca2,
            nombre="Gorra Verde",
            descripcion="No debe mostrarse",
            precio=Decimal("7.00"),
            stock=3,
            activo=False,
        )

    def test_lista_productos_muestra_solo_activos(self):
        url = reverse("productos:catalogo")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        productos = list(resp.context["productos"])
        self.assertCountEqual(
            [p.id for p in productos],
            [self.prod1.id, self.prod2.id, self.prod3.id],
        )

    def test_lista_productos_filtra_por_busqueda(self):
        url = reverse("productos:catalogo")
        # Buscar por texto en nombre
        resp = self.client.get(url, {"q": "gorra"})
        self.assertEqual(resp.status_code, 200)
        productos = list(resp.context["productos"])
        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0].id, self.prod3.id)

    def test_lista_productos_filtra_por_categoria_y_marca(self):
        url = reverse("productos:catalogo")
        resp = self.client.get(
            url,
            {"categoria": self.cat1.slug, "marca": self.marca2.slug},
        )
        self.assertEqual(resp.status_code, 200)
        productos = list(resp.context["productos"])
        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0].id, self.prod2.id)

    def test_lista_productos_contexto_incluye_categorias_y_marcas(self):
        url = reverse("productos:catalogo")
        resp = self.client.get(url)
        self.assertIn("categorias", resp.context)
        self.assertIn("marcas", resp.context)
        self.assertGreaterEqual(resp.context["categorias"].count(), 2)
        self.assertGreaterEqual(resp.context["marcas"].count(), 2)


class ListaPorCategoriaViewTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Sudaderas")
        self.marca = Marca.objects.create(nombre="Marca X")
        self.prod1 = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Sudadera Capucha",
            precio=Decimal("20.00"),
            stock=3,
            activo=True,
        )
        self.prod2 = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Sudadera Sin Capucha",
            precio=Decimal("18.00"),
            stock=0,
            activo=False,
        )

    def test_lista_por_categoria_usa_template_lista_y_filtra_activos(self):
        url = reverse("productos:catalogo_por_categoria", args=[self.cat.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        productos = list(resp.context["productos"])
        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0].id, self.prod1.id)
        self.assertEqual(resp.context["categoria"], self.cat)


# =====================================================
#   VISTA: detalle_producto
# =====================================================

class DetalleProductoViewTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Camisetas")
        self.marca = Marca.objects.create(nombre="Marca X")
        self.prod = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Camiseta Personalizada",
            precio=Decimal("15.00"),
            stock=10,
        )
        self.var1 = Variante.objects.create(
            producto=self.prod, talla="M", color="Rojo", stock=3
        )
        self.var2 = Variante.objects.create(
            producto=self.prod, talla="L", color="Rojo", stock=2
        )
        self.var3 = Variante.objects.create(
            producto=self.prod, talla="M", color="Azul", stock=1
        )

    def test_detalle_producto_contexto_con_tallas_colores_y_variantes(self):
        url = reverse("productos:producto_detalle", args=[self.prod.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["producto"], self.prod)

        tallas = resp.context["tallas"]
        colores = resp.context["colores"]
        variantes = resp.context["variantes"]

        # deben ser listas ordenadas y sin duplicados
        self.assertEqual(tallas, ["L", "M"] or ["M", "L"])
        self.assertCountEqual(tallas, ["M", "L"])
        self.assertCountEqual(colores, ["Rojo", "Azul"])
        self.assertEqual(len(variantes), 3)

    def test_detalle_producto_sin_variantes_da_listas_vacias(self):
        prod2 = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Sin variantes",
            precio=Decimal("10.00"),
            stock=5,
        )
        url = reverse("productos:producto_detalle", args=[prod2.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["tallas"], [])
        self.assertEqual(resp.context["colores"], [])
        self.assertEqual(resp.context["variantes"], [])


# =====================================================
#   URL legacy: producto_detalle_legacy
# =====================================================

class ProductoDetalleLegacyUrlTests(TestCase):
    def test_legacy_url_redirige_a_detalle(self):
        cat = Categoria.objects.create(nombre="Camisetas")
        marca = Marca.objects.create(nombre="Marca X")
        prod = Producto.objects.create(
            categoria=cat,
            marca=marca,
            nombre="Producto Legacy",
            precio=Decimal("10.00"),
            stock=5,
        )
        url_legacy = reverse("productos:producto_detalle_legacy", args=[prod.slug])
        resp = self.client.get(url_legacy)
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(
            resp.url,
            reverse("productos:producto_detalle", args=[prod.slug]),
        )


# =====================================================
#   FORMS: VarianteForm y PersonalizacionForm
# =====================================================

class FormsTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Camisetas")
        self.marca = Marca.objects.create(nombre="Marca X")
        self.prod1 = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Producto 1",
            precio=Decimal("10.00"),
            stock=5,
        )
        self.prod2 = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Producto 2",
            precio=Decimal("12.00"),
            stock=5,
        )
        self.var11 = Variante.objects.create(
            producto=self.prod1, talla="M", color="Rojo", stock=2
        )
        self.var12 = Variante.objects.create(
            producto=self.prod1, talla="L", color="Azul", stock=1
        )
        self.var21 = Variante.objects.create(
            producto=self.prod2, talla="S", color="Negro", stock=3
        )

    def test_varianteform_filtra_variante_por_producto(self):
        form = VarianteForm(producto=self.prod1)
        qs = form.fields["variante"].queryset
        self.assertCountEqual(list(qs), [self.var11, self.var12])

    def test_personalizacionform_valido_con_datos(self):
        form = PersonalizacionForm(
            data={"texto": "Hola", "color_texto": "#ff0000"}
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["texto"], "Hola")
        self.assertEqual(form.cleaned_data["color_texto"], "#ff0000")


# =====================================================
#   preview_personalizacion (vista + helpers)
# =====================================================

class PreviewPersonalizacionViewTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Camisetas")
        self.marca = Marca.objects.create(nombre="Marca X")

        # Producto sin personalización
        self.prod_sin_pers = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Sin Perso",
            precio=Decimal("10.00"),
            stock=5,
            permite_personalizacion=False,
        )

        # Producto con personalización pero sin imagen
        self.prod_sin_img = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Con Perso Sin Img",
            precio=Decimal("10.00"),
            stock=5,
            permite_personalizacion=True,
        )

        # Producto con personalización y con imagen base
        img_file = SimpleUploadedFile(
            "base.png", b"fake-image-content", content_type="image/png"
        )
        self.prod_con_img = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Con Perso Con Img",
            precio=Decimal("10.00"),
            stock=5,
            permite_personalizacion=True,
            imagen=img_file,
        )

    def test_preview_personalizacion_rechaza_producto_sin_personalizacion(self):
        url = reverse("productos:producto_preview", args=[self.prod_sin_pers.slug])
        resp = self.client.post(url, data={"texto": "Hola"})
        self.assertEqual(resp.status_code, 400)

    def test_preview_personalizacion_rechaza_producto_sin_imagen_base(self):
        url = reverse("productos:producto_preview", args=[self.prod_sin_img.slug])
        resp = self.client.post(url, data={"texto": "Hola"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b"Producto sin imagen base", resp.content)

    @patch("productos.views._generar_mockup")
    def test_preview_personalizacion_ok_sin_imagen_subida(self, mock_mockup):
        mock_mockup.return_value = "/media/mockup.png"
        url = reverse("productos:producto_preview", args=[self.prod_con_img.slug])
        resp = self.client.post(
            url,
            data={
                "texto": "Hola",
                "color_texto": "#00ff00",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["preview_url"], "/media/mockup.png")
        # _generar_mockup debe haberse llamado con la ruta de la imagen base
        mock_mockup.assert_called_once()
        args, kwargs = mock_mockup.call_args
        self.assertEqual(args[0], self.prod_con_img.imagen.path)

    @patch("productos.views._save_tmp_upload")
    @patch("productos.views._generar_mockup")
    def test_preview_personalizacion_con_imagen_subida_responde_sin_explosion(
        self, mock_mockup, mock_save_tmp
    ):
        mock_mockup.return_value = "/media/mockup2.png"
        mock_save_tmp.return_value = "/tmp/subida.png"

        url = reverse("productos:producto_preview", args=[self.prod_con_img.slug])
        img_upload = SimpleUploadedFile(
            "upload.png", b"fake-image-upload", content_type="image/png"
        )
        resp = self.client.post(
            url,
            data={
                "texto": "Hola",
                "color_texto": "#0000ff",
                "imagen": img_upload,
            },
        )
       
        self.assertEqual(resp.status_code, 400)


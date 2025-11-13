from decimal import Decimal

from django.contrib.messages import get_messages
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

from .cart import _to_dict, Cart
from .utils import get_cart, set_cart, compute_totals
from .context_processors import cart_summary
from .forms import ShippingSelectForm
from . import views

from productos.models import Categoria, Marca, Producto
from pedidos.models import ShippingMethod


class ToDictHelperTests(TestCase):
    def test_to_dict_devuelve_dict_si_ya_es_dict(self):
        data = {"a": 1}
        self.assertEqual(_to_dict(data), data)

    def test_to_dict_convierte_json_valido(self):
        value = '{"a": 1, "b": "x"}'
        result = _to_dict(value)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], "x")

    def test_to_dict_devuelve_dict_vacio_para_json_invalido(self):
        value = "{no es json}"
        result = _to_dict(value)
        self.assertEqual(result, {})

    def test_to_dict_devuelve_dict_vacio_para_none(self):
        result = _to_dict(None)
        self.assertEqual(result, {})


class CartCoreTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Camisetas")
        self.marca = Marca.objects.create(nombre="Marca X")
        self.producto = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Camiseta Roja",
            precio=Decimal("10.00"),
            stock=10,
            activo=True,
        )
        # Creamos una request con sesión
        self.factory = RequestFactory()
        self.request = self.client.get("/").wsgi_request  # session lista

    def test_add_nuevo_producto_crea_linea(self):
        cart = Cart(self.request)
        cart.add(self.producto, quantity=2)
        session_cart = self.request.session.get("cart", {})
        self.assertIn(str(self.producto.id), session_cart)
        self.assertEqual(session_cart[str(self.producto.id)]["qty"], 2)
        self.assertEqual(len(cart), 2)
        self.assertEqual(cart.total, Decimal("20.00"))

    def test_add_suma_cantidades_por_defecto(self):
        cart = Cart(self.request)
        cart.add(self.producto, quantity=1)
        cart.add(self.producto, quantity=3)
        session_cart = self.request.session["cart"]
        self.assertEqual(session_cart[str(self.producto.id)]["qty"], 4)

    def test_add_con_override_reemplaza_cantidad(self):
        cart = Cart(self.request)
        cart.add(self.producto, quantity=1)
        cart.add(self.producto, quantity=5, override=True)
        session_cart = self.request.session["cart"]
        self.assertEqual(session_cart[str(self.producto.id)]["qty"], 5)

    def test_set_fija_cantidad_y_borra_si_cero(self):
        cart = Cart(self.request)
        cart.add(self.producto, quantity=3)
        cart.set(self.producto, quantity=1)
        session_cart = self.request.session["cart"]
        self.assertEqual(session_cart[str(self.producto.id)]["qty"], 1)

        # Si ponemos 0, debe eliminar la línea
        cart.set(self.producto, quantity=0)
        session_cart = self.request.session["cart"]
        self.assertNotIn(str(self.producto.id), session_cart)

    def test_remove_elimina_linea(self):
        cart = Cart(self.request)
        cart.add(self.producto, quantity=2)
        cart.remove(self.producto)
        session_cart = self.request.session["cart"]
        self.assertNotIn(str(self.producto.id), session_cart)

    def test_iterador_devuelve_items_con_producto_y_subtotal(self):
        cart = Cart(self.request)
        cart.add(self.producto, quantity=2)
        items = list(iter(cart))
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["product"], self.producto)
        self.assertEqual(item["qty"], 2)
        self.assertEqual(item["subtotal"], Decimal("20.00"))



class CartStockHelpersTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Camisetas")
        self.marca = Marca.objects.create(nombre="Marca X")
        self.p1 = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Producto 1",
            precio=Decimal("10.00"),
            stock=1,
            activo=True,
        )
        self.p2 = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Producto 2",
            precio=Decimal("5.00"),
            stock=0,
            activo=True,
        )
        self.request = self.client.get("/").wsgi_request

    def test_stock_errors_detecta_lineas_con_mas_cantidad_que_stock(self):
        cart = Cart(self.request)
        cart.add(self.p1, quantity=3)  # stock=1
        errores = cart.stock_errors()
        self.assertEqual(len(errores), 1)
        self.assertEqual(errores[0]["product"], self.p1)
        self.assertEqual(errores[0]["qty"], 3)
        self.assertEqual(errores[0]["disponible"], 1)
        self.assertTrue(cart.has_stock_errors())

    def test_normalize_to_stock_recorta_y_elimina(self):
        cart = Cart(self.request)
        # p1: stock 1, metemos 3
        cart.add(self.p1, quantity=3)
        # p2: stock 0, metemos 1
        cart.add(self.p2, quantity=1)
        ajustadas = cart.normalize_to_stock()
        # Ambas líneas deben ser ajustadas (p1 recortado, p2 eliminado)
        self.assertEqual(ajustadas, 2)

        session_cart = self.request.session.get("cart", {})
        # p2 eliminado
        self.assertNotIn(str(self.p2.id), session_cart)
        # p1 recortado a 1
        self.assertEqual(session_cart[str(self.p1.id)]["qty"], 1)


class CartUtilsTests(TestCase):
    def setUp(self):
        self.request = self.client.get("/").wsgi_request

    def test_get_cart_devuelve_estructura_por_defecto_si_no_hay_sesion(self):
        cart = get_cart(self.request)
        self.assertEqual(cart["items"], [])
        self.assertIsNone(cart["shipping_method"])

    def test_set_cart_guarda_en_sesion(self):
        cart_data = {"items": [{"precio": "10.00", "qty": 2}], "shipping_method": None}
        set_cart(self.request, cart_data)
        self.assertIn("cart", self.request.session)
        self.assertEqual(self.request.session["cart"]["items"][0]["qty"], 2)

    @override_settings(ENVIO_GRATIS_DESDE=Decimal("50.00"))
    def test_compute_totals_con_envio_y_sin_gratis(self):
        method = ShippingMethod.objects.create(
            nombre="Estándar",
            slug="std",
            coste=Decimal("5.00"),
            activo=True,
            orden=1,
        )
        cart_data = {
            "items": [
                {"precio": "10.00", "qty": 2},
            ],
            "shipping_method": method.id,
        }
        set_cart(self.request, cart_data)
        result = compute_totals(self.request)
        self.assertEqual(result["subtotal"], Decimal("20.00"))
        self.assertEqual(result["shipping_cost"], Decimal("5.00"))
        self.assertEqual(result["total"], Decimal("25.00"))
        self.assertEqual(result["method"], method)

    @override_settings(ENVIO_GRATIS_DESDE=Decimal("20.00"))
    def test_compute_totals_con_envio_gratis(self):
        method = ShippingMethod.objects.create(
            nombre="Estándar",
            slug="std",
            coste=Decimal("5.00"),
            activo=True,
            orden=1,
        )
        cart_data = {
            "items": [
                {"precio": "10.00", "qty": 2},  # subtotal = 20
            ],
            "shipping_method": method.id,
        }
        set_cart(self.request, cart_data)
        result = compute_totals(self.request)
        self.assertEqual(result["subtotal"], Decimal("20.00"))
        self.assertEqual(result["shipping_cost"], Decimal("0.00"))
        self.assertEqual(result["total"], Decimal("20.00"))



class CartContextProcessorTests(TestCase):
    @override_settings(MONEDA="EUR")
    def test_cart_summary_calcula_count_y_total(self):
        request = self.client.get("/").wsgi_request
        request.session["cart"] = {
            "1": {"qty": 2, "price": "10.00"},
            "2": {"qty": 1, "price": "5.00"},
        }
        result = cart_summary(request)
        self.assertEqual(result["cart_count"], 3)
        self.assertEqual(result["cart_total"], Decimal("25.00"))
        self.assertEqual(result["MONEDA"], "EUR")



class ShippingSelectFormTests(TestCase):
    def setUp(self):
        self.m1 = ShippingMethod.objects.create(
            nombre="Estándar",
            slug="std",
            coste=Decimal("5.00"),
            activo=True,
            orden=2,
        )
        self.m2 = ShippingMethod.objects.create(
            nombre="Express",
            slug="exp",
            coste=Decimal("10.00"),
            activo=True,
            orden=1,
        )
        self.m3 = ShippingMethod.objects.create(
            nombre="Inactivo",
            slug="off",
            coste=Decimal("3.00"),
            activo=False,
            orden=3,
        )

    def test_shippingselectform_filtra_activos_y_usa_orden(self):
        form = ShippingSelectForm()
        qs = form.fields["shipping_method"].queryset
        self.assertQuerysetEqual(
            qs,
            [self.m2, self.m1],
            transform=lambda x: x,
        )


class CarritoViewsTests(TestCase):
    def setUp(self):
        self.cat = Categoria.objects.create(nombre="Camisetas")
        self.marca = Marca.objects.create(nombre="Marca X")
        self.producto = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Camiseta Azul",
            precio=Decimal("10.00"),
            stock=5,
            activo=True,
        )
        self.producto_sin_stock = Producto.objects.create(
            categoria=self.cat,
            marca=self.marca,
            nombre="Camiseta Sin Stock",
            precio=Decimal("8.00"),
            stock=0,
            activo=True,
        )

    def test_carrito_ver_responde_200_y_contiene_cart_en_contexto(self):
        url = reverse("carrito:carrito_ver")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("cart", resp.context)
        self.assertIn("stock_errores", resp.context)

    def test_carrito_add_normal_añade_producto(self):
        url_add = reverse("carrito:carrito_add", args=[self.producto.id])
        resp_post = self.client.post(url_add, {"quantity": 2})
        self.assertEqual(resp_post.status_code, 302)

        # Mensaje de éxito
        messages = list(get_messages(resp_post.wsgi_request))
        texts = [m.message for m in messages]
        self.assertTrue(any("Producto añadido" in t for t in texts))

        # Comprobamos el contenido real del carrito
        resp_get = self.client.get(reverse("carrito:carrito_ver"))
        cart = resp_get.context["cart"]
        items = list(cart)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["qty"], 2)

    def test_carrito_add_no_permite_superar_stock(self):
        # Primero añadimos 4 (stock=5)
        url_add = reverse("carrito:carrito_add", args=[self.producto.id])
        self.client.post(url_add, {"quantity": 4})
        # Ahora pedimos 5 más -> solo debería añadir 1 (total 5)
        resp_post = self.client.post(url_add, {"quantity": 5})
        self.assertEqual(resp_post.status_code, 302)
        messages = list(get_messages(resp_post.wsgi_request))
        texts = [m.message for m in messages]
        self.assertTrue(any("Solo quedaban" in t for t in texts))

        resp_get = self.client.get(reverse("carrito:carrito_ver"))
        cart = resp_get.context["cart"]
        items = list(cart)
        self.assertEqual(items[0]["qty"], 5)  # topado al stock

    def test_carrito_add_sin_stock_muestra_error_y_no_añade(self):
        url_add = reverse("carrito:carrito_add", args=[self.producto_sin_stock.id])
        resp_post = self.client.post(url_add, {"quantity": 1})
        self.assertEqual(resp_post.status_code, 302)
        messages = list(get_messages(resp_post.wsgi_request))
        texts = [m.message for m in messages]
        self.assertTrue(any("No queda stock" in t for t in texts))

        resp_get = self.client.get(reverse("carrito:carrito_ver"))
        cart = resp_get.context["cart"]
        self.assertEqual(len(list(cart)), 0)

    def test_carrito_update_cantidad_a_cero_elimina_linea(self):
        # añadimos primero
        url_add = reverse("carrito:carrito_add", args=[self.producto.id])
        self.client.post(url_add, {"quantity": 2})

        url_update = reverse("carrito:carrito_update", args=[self.producto.id])
        resp_post = self.client.post(url_update, {"quantity": 0})
        self.assertEqual(resp_post.status_code, 302)
        messages = list(get_messages(resp_post.wsgi_request))
        texts = [m.message for m in messages]
        self.assertTrue(any("Quitado" in t for t in texts))

        resp_get = self.client.get(reverse("carrito:carrito_ver"))
        cart = resp_get.context["cart"]
        self.assertEqual(len(list(cart)), 0)

    def test_carrito_update_topa_a_stock_si_piden_de_mas(self):
        url_add = reverse("carrito:carrito_add", args=[self.producto.id])
        self.client.post(url_add, {"quantity": 1})

        url_update = reverse("carrito:carrito_update", args=[self.producto.id])
        resp_post = self.client.post(url_update, {"quantity": 10})
        self.assertEqual(resp_post.status_code, 302)
        messages = list(get_messages(resp_post.wsgi_request))
        texts = [m.message for m in messages]
        self.assertTrue(any("Sin stock suficiente" in t for t in texts))

        resp_get = self.client.get(reverse("carrito:carrito_ver"))
        cart = resp_get.context["cart"]
        items = list(cart)
        self.assertEqual(items[0]["qty"], 5)  # el stock del producto

    def test_carrito_remove_elimina_producto(self):
        url_add = reverse("carrito:carrito_add", args=[self.producto.id])
        self.client.post(url_add, {"quantity": 2})

        url_remove = reverse("carrito:carrito_remove", args=[self.producto.id])
        resp_post = self.client.post(url_remove)
        self.assertEqual(resp_post.status_code, 302)
        messages = list(get_messages(resp_post.wsgi_request))
        texts = [m.message for m in messages]
        self.assertTrue(any("Producto eliminado" in t for t in texts))

        resp_get = self.client.get(reverse("carrito:carrito_ver"))
        cart = resp_get.context["cart"]
        self.assertEqual(len(list(cart)), 0)

    def test_carrito_clear_vacia_carrito(self):
        # añadimos algo
        url_add = reverse("carrito:carrito_add", args=[self.producto.id])
        self.client.post(url_add, {"quantity": 2})

    
        request = self.client.post("/").wsgi_request
        request.session = self.client.session
        response = views.carrito_clear(request)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("cart", request.session)

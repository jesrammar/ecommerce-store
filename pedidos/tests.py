# pedidos/tests.py
from __future__ import annotations
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

from .models import Pedido, PedidoItem, ShippingMethod
from . import services
from .views import stripe_webhook


class PedidoModelTests(TestCase):
    def _create_pedido(self, **extra):
        data = {
            "email": "cliente@example.com",
            "nombre": "Cliente Test",
            "telefono": "",
            "direccion": "Calle Falsa 123",
            "ciudad": "Madrid",
            "cp": "28001",
        }
        data.update(extra)
        return Pedido.objects.create(**data)

    def test_pedido_str(self):
        pedido = self._create_pedido()
        self.assertEqual(str(pedido), f"Pedido #{pedido.id} - {pedido.email}")

    def test_pedido_save_generates_tracking_token(self):
        pedido = self._create_pedido()
        self.assertTrue(pedido.tracking_token)
        self.assertEqual(len(pedido.tracking_token), 32)

        pedido2 = self._create_pedido(email="otro@example.com")
        pedido2.tracking_token = "x" * 32
        pedido2.save()
        self.assertEqual(pedido2.tracking_token, "x" * 32)

    def test_model_has_field_helper(self):
        self.assertTrue(services._model_has_field(Pedido, "total"))
        self.assertFalse(services._model_has_field(Pedido, "no_existe"))


class PedidoItemModelTests(TestCase):
    def setUp(self):
        self.pedido = Pedido.objects.create(
            email="cliente@example.com",
            nombre="Cliente Test",
            telefono="",
            direccion="Calle Falsa 123",
            ciudad="Madrid",
            cp="28001",
        )

    def test_pedidoitem_save_calcula_subtotal_si_es_cero(self):
        item = PedidoItem.objects.create(
            pedido=self.pedido,
            producto_id=1,
            titulo="Producto Test",
            precio_unit=Decimal("10.00"),
            cantidad=2,
            subtotal=Decimal("0.00"),
        )
        self.assertEqual(item.subtotal, Decimal("20.00"))

    def test_pedidoitem_save_respeta_subtotal_si_ya_tiene_valor(self):
        item = PedidoItem.objects.create(
            pedido=self.pedido,
            producto_id=1,
            titulo="Producto Test",
            precio_unit=Decimal("10.00"),
            cantidad=2,
            subtotal=Decimal("15.00"),
        )
        self.assertEqual(item.subtotal, Decimal("15.00"))

    def test_pedidoitem_str(self):
        item = PedidoItem.objects.create(
            pedido=self.pedido,
            producto_id=1,
            titulo="Producto Test",
            precio_unit=Decimal("10.00"),
            cantidad=3,
            subtotal=Decimal("30.00"),
        )
        self.assertEqual(str(item), "Producto Test x3")

class ServiceHelpersTests(TestCase):
    def test_meta_dict_acepta_dict(self):
        data = {"a": 1}
        self.assertEqual(services._meta_dict(data), data)

    def test_meta_dict_parsea_json_valido(self):
        s = '{"talla": "M", "color": "Rojo"}'
        result = services._meta_dict(s)
        self.assertEqual(result["talla"], "M")
        self.assertEqual(result["color"], "Rojo")

    def test_meta_dict_json_invalido_devuelve_dict_vacio(self):
        result = services._meta_dict("{no es json}")
        self.assertEqual(result, {})

    def test_meta_dict_otro_tipo_devuelve_dict_vacio(self):
        result = services._meta_dict(123)
        self.assertEqual(result, {})

    def test_to_int_safe_varios_tipos(self):
        self.assertEqual(services._to_int_safe("5"), 5)
        self.assertEqual(services._to_int_safe(Decimal("7")), 7)
        self.assertEqual(services._to_int_safe(None, default=3), 3)
        self.assertEqual(services._to_int_safe("no-num", default=9), 9)

    def test_precio_unitario_usa_price_del_item_si_existe(self):
        item = {"price": "12.34"}
        base = Decimal("10.00")
        result = services._precio_unitario(item, base, variante=None)
        self.assertEqual(result, Decimal("12.34"))

    def test_precio_unitario_suma_extra_de_variante(self):
        class V:
            extra_precio = Decimal("2.50")

        item = {}
        base = Decimal("10.00")
        result = services._precio_unitario(item, base, variante=V())
        self.assertEqual(result, Decimal("12.50"))

    def test_subtotal_linea_usa_subtotal_del_item_si_existe(self):
        item = {"subtotal": "33.33"}
        result = services._subtotal_linea(item, Decimal("1.00"), 5)
        self.assertEqual(result, Decimal("33.33"))

    def test_subtotal_linea_calcula_si_no_hay_subtotal(self):
        item = {}
        result = services._subtotal_linea(item, Decimal("2.50"), 4)
        self.assertEqual(result, Decimal("10.00"))

    def test_pedidoitem_kwargs_base_no_incluye_meta_si_modelo_no_tiene_campo(self):
        pedido = Pedido.objects.create(
            email="c@example.com",
            nombre="Test",
            telefono="",
            direccion="Dir",
            ciudad="Ciudad",
            cp="00000",
        )

        class Prod:
            id = 1
            nombre = "Producto X"

        kwargs = services._pedidoitem_kwargs_base(
            pedido, Prod(), Decimal("9.99"), 2, Decimal("19.98"), {"x": 1}
        )
        self.assertEqual(
            kwargs,
            {
                "pedido": pedido,
                "producto_id": 1,
                "titulo": "Producto X",
                "precio_unit": Decimal("9.99"),
                "cantidad": 2,
                "subtotal": Decimal("19.98"),
            },
        )


class FakeProducto:
    def __init__(self, pk, nombre, precio, stock):
        self.id = pk
        self.nombre = nombre
        self.precio = Decimal(str(precio))
        self.stock = stock
        self.save_called = False

    def save(self, *args, **kwargs):
        # solo marcamos que se ha llamado, para no romper nada
        self.save_called = True


class FakeCart:
    """
    Sustituye al carrito real. Se parchea en services y views.
    Usa la lista de items que se le asigna a nivel de clase.
    """
    items = []

    def __init__(self, request):
        pass

    def __iter__(self):
        return iter(self.items)

    def count(self):
        return len(self.items)

    def clear(self):
        self.cleared = True


@override_settings(ENVIO_GRATIS_DESDE=Decimal("100.00"))
class CrearPedidoDesdeCarritoTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="pepe", email="pepe@example.com", password="1234"
        )
        self.method = ShippingMethod.objects.create(
            nombre="Envío estándar",
            slug="envio",
            coste=Decimal("5.00"),
            activo=True,
            orden=1,
        )

    def _build_request(self):
        req = self.factory.get("/")
        req.session = {"shipping_method_id": self.method.id}
        req.user = self.user
        return req

    def test_error_si_carrito_vacio(self):
        from .services import crear_pedido_desde_carrito

        FakeCart.items = []
        request = self._build_request()
        with patch("pedidos.services.Cart", new=FakeCart):
            with self.assertRaises(ValueError):
                crear_pedido_desde_carrito(
                    request,
                    {
                        "email": "c@example.com",
                        "nombre": "Cliente",
                        "telefono": "",
                        "direccion": "Dir",
                        "ciudad": "Ciudad",
                        "cp": "00000",
                    },
                )

    def test_crea_pedido_y_linea_con_envio_y_usuario(self):
        from .services import crear_pedido_desde_carrito

        producto = FakeProducto(1, "Camisa", "10.00", stock=5)
        FakeCart.items = [
            {"product": producto, "qty": 2, "meta": {}},
        ]
        request = self._build_request()

        with patch("pedidos.services.Cart", new=FakeCart):
            pedido = crear_pedido_desde_carrito(
                request,
                {
                    "email": "c@example.com",
                    "nombre": "Cliente",
                    "telefono": "",
                    "direccion": "Dir",
                    "ciudad": "Ciudad",
                    "cp": "00000",
                    "pago_metodo": "contrareembolso",
                },
            )

        # Pedido asociado al usuario
        self.assertEqual(pedido.usuario, self.user)

        # Subtotal = 2 * 10 = 20, envío = 5, total = 25
        self.assertEqual(pedido.envio_metodo, self.method)
        self.assertEqual(pedido.envio_coste, Decimal("5.00"))
        self.assertEqual(pedido.total, Decimal("25.00"))

        # Se creó una línea
        self.assertEqual(pedido.items.count(), 1)
        linea = pedido.items.first()
        self.assertEqual(linea.cantidad, 2)
        self.assertEqual(linea.subtotal, Decimal("20.00"))

        # El producto ha bajado stock
        self.assertEqual(producto.stock, 3)

        # La sesión ya no tiene shipping_method_id
        self.assertNotIn("shipping_method_id", request.session)

    def test_error_si_no_hay_stock_suficiente(self):
        from .services import crear_pedido_desde_carrito

        producto = FakeProducto(1, "Camisa", "10.00", stock=1)
        FakeCart.items = [
            {"product": producto, "qty": 3, "meta": {}},
        ]
        request = self._build_request()

        with patch("pedidos.services.Cart", new=FakeCart):
            with self.assertRaises(ValueError) as ctx:
                crear_pedido_desde_carrito(
                    request,
                    {
                        "email": "c@example.com",
                        "nombre": "Cliente",
                        "telefono": "",
                        "direccion": "Dir",
                        "ciudad": "Ciudad",
                        "cp": "00000",
                    },
                )
        self.assertIn("Sin stock suficiente", str(ctx.exception))


@override_settings(ENVIO_GRATIS_DESDE=Decimal("100.00"))
class CrearPedidoTarjetaPreTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="lola", email="lola@example.com", password="1234"
        )
        self.method = ShippingMethod.objects.create(
            nombre="Envío estándar",
            slug="envio",
            coste=Decimal("5.00"),
            activo=True,
            orden=1,
        )

    def _build_request(self):
        req = self.factory.get("/")
        req.session = {"shipping_method_id": self.method.id}
        req.user = self.user
        return req

    def test_error_si_carrito_vacio(self):
        FakeCart.items = []
        request = self._build_request()

        with patch("pedidos.services.Cart", new=FakeCart):
            with self.assertRaises(ValueError):
                services.crear_pedido_tarjeta_pre(
                    request,
                    {
                        "email": "c@example.com",
                        "nombre": "Cliente",
                        "telefono": "",
                        "direccion": "Dir",
                        "ciudad": "Ciudad",
                        "cp": "00000",
                    },
                )

    def test_crea_pedido_tarjeta_en_estado_iniciado(self):
        producto = FakeProducto(1, "Pantalón", "20.00", stock=10)
        FakeCart.items = [
            {"product": producto, "qty": 1, "meta": {}},
        ]
        request = self._build_request()

        with patch("pedidos.services.Cart", new=FakeCart):
            pedido, totales = services.crear_pedido_tarjeta_pre(
                request,
                {
                    "email": "c@example.com",
                    "nombre": "Cliente",
                    "telefono": "",
                    "direccion": "Dir",
                    "ciudad": "Ciudad",
                    "cp": "00000",
                },
            )

        self.assertEqual(pedido.usuario, self.user)
        self.assertEqual(pedido.pago_metodo, "tarjeta")
        self.assertEqual(pedido.pago_estado, "iniciado")

        # Subtotal 20, envío 5, total 25
        self.assertEqual(totales["subtotal"], Decimal("20.00"))
        self.assertEqual(totales["shipping_cost"], Decimal("5.00"))
        self.assertEqual(totales["total"], Decimal("25.00"))
        self.assertEqual(pedido.total, Decimal("25.00"))


class CheckoutViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="ana", email="ana@example.com", password="1234"
        )

    def test_checkout_datos_get_200(self):
        response = self.client.get(reverse("pedidos:checkout_datos"))
        self.assertEqual(response.status_code, 200)

    def test_checkout_datos_post_guarda_datos_en_sesion_y_redirige(self):
        data = {
            "nombre": "Ana",
            "apellidos": "García",
            "email": "ana@example.com",
            "telefono": "123",
            "direccion": "Calle",
            "ciudad": "Ciudad",
            "cp": "00000",
            "provincia": "Provincia",
        }
        response = self.client.post(reverse("pedidos:checkout_datos"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("pedidos:checkout_pago")
        )
        session = self.client.session
        self.assertIn("checkout_pago", session)
        self.assertEqual(session["checkout_pago"]["nombre"], "Ana")

    @override_settings(ENVIO_GRATIS_DESDE=Decimal("100.00"))
    @patch("pedidos.views.Cart", new=FakeCart)
    def test_checkout_pago_get_muestra_totales(self):
        # Preparamos datos de sesión
        session = self.client.session
        session["checkout_pago"] = {
            "nombre": "Ana",
            "apellidos": "G",
            "email": "ana@example.com",
            "telefono": "",
            "direccion": "Dir",
            "ciudad": "Ciu",
            "cp": "00000",
            "provincia": "Prov",
        }
        method = ShippingMethod.objects.create(
            nombre="Estándar",
            slug="std",
            coste=Decimal("5.00"),
            activo=True,
            orden=1,
        )
        session["shipping_method_id"] = method.id
        session.save()

        # carrito con 2 x 10 = 20
        FakeCart.items = [
            {"product": FakeProducto(1, "Camisa", "10.00", stock=5), "qty": 2},
        ]
        response = self.client.get(reverse("pedidos:checkout_pago"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["subtotal"], Decimal("20.00"))
        self.assertEqual(response.context["envio"], Decimal("5.00"))
        self.assertEqual(response.context["total_preview"], Decimal("25.00"))

    @override_settings(ENVIO_GRATIS_DESDE=Decimal("100.00"))
    @patch("pedidos.views.Cart", new=FakeCart)
    @patch("pedidos.views._enviar_email_confirmacion")
    @patch("pedidos.views.crear_pedido_desde_carrito")
    def test_checkout_pago_post_crea_pedido_y_redirige_ok(
        self,
        mock_crear,
        mock_email,
    ):
        # Datos en sesión
        session = self.client.session
        session["checkout_pago"] = {
            "nombre": "Ana",
            "apellidos": "G",
            "email": "ana@example.com",
            "telefono": "",
            "direccion": "Dir",
            "ciudad": "Ciu",
            "cp": "00000",
            "provincia": "Prov",
        }
        session.save()

        pedido = Pedido.objects.create(
            email="ana@example.com",
            nombre="Ana",
            telefono="",
            direccion="Dir",
            ciudad="Ciu",
            cp="00000",
        )
        mock_crear.return_value = pedido

        FakeCart.items = [
            {"product": FakeProducto(1, "Camisa", "10.00", stock=5), "qty": 1},
        ]

        response = self.client.post(reverse("pedidos:checkout_pago"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("pedidos:checkout_ok", args=[pedido.id])
        )
        mock_crear.assert_called_once()
        mock_email.assert_called_once_with(pedido, ANY := mock_email.call_args[0][1])
        # sólo comprobamos que se ha llamado; el segundo argumento es el request


class StripeWebhookTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("pedidos.views._enviar_email_confirmacion")
    @patch("pedidos.views.confirmar_pedido_tarjeta_exitoso")
    @patch("pedidos.views.stripe.Webhook.construct_event")
    def test_webhook_payment_intent_succeeded_actualiza_pedido(
        self,
        mock_construct_event,
        mock_confirmar,
        mock_email,
    ):
        pedido = Pedido.objects.create(
            email="c@example.com",
            nombre="Cliente",
            telefono="",
            direccion="Dir",
            ciudad="Ciudad",
            cp="00000",
            pago_ref="pi_123",
        )

        event = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123",
                    "metadata": {"pedido_id": str(pedido.id)},
                }
            },
        }
        mock_construct_event.return_value = event

        request = self.factory.post(
            reverse("pedidos:stripe_webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="dummy",
        )

        response = stripe_webhook(request)
        self.assertEqual(response.status_code, 200)
        mock_confirmar.assert_called_once_with(pedido)
        mock_email.assert_called_once_with(pedido)


class MisPedidosViewsTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="user1", email="u1@example.com", password="1234"
        )
        self.other = self.User.objects.create_user(
            username="user2", email="u2@example.com", password="1234"
        )

        # pedidos de ambos usuarios
        self.p1 = Pedido.objects.create(
            usuario=self.user,
            email="u1@example.com",
            nombre="U1",
            telefono="",
            direccion="Dir",
            ciudad="Ciudad",
            cp="00000",
        )
        self.p2 = Pedido.objects.create(
            usuario=self.user,
            email="u1@example.com",
            nombre="U1-bis",
            telefono="",
            direccion="Dir",
            ciudad="Ciudad",
            cp="00000",
        )
        self.p_other = Pedido.objects.create(
            usuario=self.other,
            email="u2@example.com",
            nombre="U2",
            telefono="",
            direccion="Dir",
            ciudad="Ciudad",
            cp="00000",
        )

    def test_mis_pedidos_solo_muestra_los_del_usuario_logueado(self):
        self.client.login(username="user1", password="1234")
        response = self.client.get(reverse("pedidos:mis_pedidos"))
        self.assertEqual(response.status_code, 200)
        pedidos = list(response.context["pedidos"])
        self.assertEqual({p.id for p in pedidos}, {self.p1.id, self.p2.id})

    def test_pedido_detalle_usuario_no_permite_ver_ajenos(self):
        # user1 logueado intenta ver pedido de otro
        self.client.login(username="user1", password="1234")
        response = self.client.get(
            reverse("pedidos:pedido_detalle_usuario", args=[self.p_other.id])
        )
        # debería devolver 404
        self.assertEqual(response.status_code, 404)

    def test_pedido_detalle_usuario_ok_para_propio_pedido(self):
        self.client.login(username="user1", password="1234")
        response = self.client.get(
            reverse("pedidos:pedido_detalle_usuario", args=[self.p1.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["pedido"].id, self.p1.id)

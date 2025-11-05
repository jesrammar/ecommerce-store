from __future__ import annotations
import json
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from carrito.cart import Cart
from productos.models import Producto
try:
    from productos.models import Variante  # type: ignore
except Exception:
    Variante = None

from .models import Pedido, PedidoItem, ShippingMethod


def _model_has_field(model, name: str) -> bool:
    return any(f.name == name for f in model._meta.get_fields())


def _meta_dict(meta) -> dict:
    if meta is None or isinstance(meta, dict):
        return meta or {}
    if isinstance(meta, str):
        try:
            return json.loads(meta)
        except Exception:
            return {}
    return {}


def _resolver_variante(producto_id: int, meta: dict):
    meta = _meta_dict(meta)
    talla = meta.get("talla") or meta.get("var_talla")
    color = meta.get("color") or meta.get("var_color")
    if not Variante or (not talla and not color):
        return None, None, None
    qs = Variante.objects.filter(producto_id=producto_id)
    if talla:
        qs = qs.filter(talla=talla)
    if color:
        qs = qs.filter(color=color)
    return qs.first(), talla, color


def _to_int_safe(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return int(value)
        s = str(value).strip()
        return int(s) if s else default
    except (TypeError, ValueError):
        return default


def _precio_unitario(item: dict, base_precio: Decimal, variante=None) -> Decimal:
    if item.get("price") is not None:
        return Decimal(str(item["price"]))
    extra = getattr(variante, "extra_precio", Decimal("0.00")) or Decimal("0.00")
    return (Decimal(base_precio) + Decimal(extra)).quantize(Decimal("0.01"))


def _subtotal_linea(item: dict, precio_unit: Decimal, qty: int) -> Decimal:
    if item.get("subtotal") is not None:
        return Decimal(str(item["subtotal"]))
    return (Decimal(precio_unit) * Decimal(qty)).quantize(Decimal("0.01"))


def _pedidoitem_kwargs_base(
    pedido: Pedido,
    producto: Producto,
    precio_unit: Decimal,
    qty: int,
    subtotal: Decimal,
    meta: dict,
) -> dict:
    data = {
        "pedido": pedido,
        "producto_id": producto.id,
        "titulo": producto.nombre,
        "precio_unit": precio_unit,
        "cantidad": qty,
        "subtotal": subtotal,
    }
    if _model_has_field(PedidoItem, "meta"):
        data["meta"] = meta
    return data


@transaction.atomic
def crear_pedido_desde_carrito(request, datos: dict) -> Pedido:
    """
    Crea un pedido para pago contrareembolso a partir del carrito.
    Ahora, si el usuario está logueado y el modelo tiene campo `usuario`,
    se asocia ese usuario al pedido.
    """
    cart = Cart(request)
    if cart.count() == 0:
        raise ValueError("El carrito está vacío")

    # ---------- nuevo: construimos kwargs y añadimos usuario si existe ----------
    pedido_kwargs = dict(
        email=datos["email"],
        nombre=datos["nombre"],
        telefono=datos.get("telefono", ""),
        direccion=datos["direccion"],
        ciudad=datos["ciudad"],
        cp=datos["cp"],
        total=Decimal("0.00"),
        pago_metodo=datos.get("pago_metodo", "contrareembolso"),
        pago_estado="pendiente",
    )
    if _model_has_field(Pedido, "usuario") and request.user.is_authenticated:
        pedido_kwargs["usuario"] = request.user

    pedido = Pedido.objects.create(**pedido_kwargs)
    # ---------------------------------------------------------------------------

    subtotal = Decimal("0.00")
    for item in cart:
        producto = item.get("product") or Producto.objects.get(
            pk=item.get("product_id")
        )
        qty = _to_int_safe(item.get("qty"), 0)
        if qty <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")

        meta = _meta_dict(item.get("meta"))
        variante, _, _ = _resolver_variante(producto.id, meta)

        if variante:
            disponible = _to_int_safe(getattr(variante, "stock", 0), 0)
            if qty > disponible:
                nombre_var = (
                    f"{getattr(variante, 'talla', '-')}/"
                    f"{getattr(variante, 'color', '-')}"
                )
                raise ValueError(
                    f"Sin stock suficiente para {producto.nombre} "
                    f"({nombre_var}). Disponible: {disponible}."
                )
        else:
            disponible = _to_int_safe(getattr(producto, "stock", 0), 0)
            if qty > disponible:
                raise ValueError(
                    f"Sin stock suficiente para {producto.nombre}. "
                    f"Disponible: {disponible}."
                )

        price_unit = _precio_unitario(
            item, base_precio=producto.precio, variante=variante
        )
        line_total = _subtotal_linea(item, price_unit, qty)

        if variante:
            variante.stock = disponible - qty
            variante.save(update_fields=["stock"])
        else:
            producto.stock = disponible - qty
            producto.save(update_fields=["stock"])

        kwargs = _pedidoitem_kwargs_base(
            pedido, producto, price_unit, qty, line_total, meta
        )
        PedidoItem.objects.create(**kwargs)
        subtotal += line_total

    shipping_cost = Decimal("0.00")
    method = None
    method_id = request.session.get("shipping_method_id")
    if method_id:
        method = ShippingMethod.objects.filter(pk=method_id, activo=True).first()

    ENVIO_GRATIS_DESDE = getattr(
        settings, "ENVIO_GRATIS_DESDE", Decimal("999999")
    )
    if subtotal < ENVIO_GRATIS_DESDE and method:
        shipping_cost = Decimal(method.coste)

    pedido.envio_metodo = method
    pedido.envio_coste = shipping_cost
    pedido.total = subtotal + shipping_cost
    pedido.save(update_fields=["envio_metodo", "envio_coste", "total"])

    # vaciar carrito y limpiar sesión
    try:
        cart.clear()
    except Exception:
        pass
    for k in ("checkout_datos", "checkout_pago", "shipping_method_id"):
        request.session.pop(k, None)

    # ⚠️ El email de confirmación se envía ahora desde las views
    # _enviar_email_confirmacion(pedido)

    return pedido


@transaction.atomic
def crear_pedido_tarjeta_pre(request, datos: dict):
    """
    Crea un pedido en estado 'iniciado' para pago con tarjeta (Stripe).
    También asocia `usuario` si el modelo lo tiene y hay usuario autenticado.
    """
    cart = Cart(request)
    if cart.count() == 0:
        raise ValueError("El carrito está vacío")

    # ---------- nuevo: kwargs + usuario ----------
    pedido_kwargs = dict(
        email=datos["email"],
        nombre=datos["nombre"],
        telefono=datos.get("telefono", ""),
        direccion=datos["direccion"],
        ciudad=datos["ciudad"],
        cp=datos["cp"],
        total=Decimal("0.00"),
        pago_metodo="tarjeta",
        pago_estado="iniciado",
    )
    if _model_has_field(Pedido, "usuario") and request.user.is_authenticated:
        pedido_kwargs["usuario"] = request.user

    pedido = Pedido.objects.create(**pedido_kwargs)
    # --------------------------------------------

    subtotal = Decimal("0.00")
    for item in cart:
        producto = item.get("product") or Producto.objects.get(
            pk=item.get("product_id")
        )
        qty = _to_int_safe(item.get("qty"), 0)
        meta = _meta_dict(item.get("meta"))
        variante, _, _ = _resolver_variante(producto.id, meta)

        price_unit = _precio_unitario(
            item, base_precio=producto.precio, variante=variante
        )
        line_total = _subtotal_linea(item, price_unit, qty)

        kwargs = _pedidoitem_kwargs_base(
            pedido, producto, price_unit, qty, line_total, meta
        )
        PedidoItem.objects.create(**kwargs)
        subtotal += line_total

    shipping_cost = Decimal("0.00")
    method = None
    method_id = request.session.get("shipping_method_id")
    if method_id:
        method = ShippingMethod.objects.filter(pk=method_id, activo=True).first()

    ENVIO_GRATIS_DESDE = getattr(
        settings, "ENVIO_GRATIS_DESDE", Decimal("999999")
    )
    if subtotal < ENVIO_GRATIS_DESDE and method:
        shipping_cost = Decimal(method.coste)

    pedido.envio_metodo = method
    pedido.envio_coste = shipping_cost
    pedido.total = subtotal + shipping_cost
    pedido.save(update_fields=["envio_metodo", "envio_coste", "total"])

    return pedido, {
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "total": pedido.total,
    }


def confirmar_pedido_tarjeta_exitoso(pedido: Pedido) -> None:
    if pedido.pago_estado == "pagado":
        return

    for it in pedido.items.select_related("producto"):
        producto = it.producto
        meta = getattr(it, "meta", {}) or {}
        var_id = meta.get("variante_id") or meta.get("id_variante")

        if Variante and var_id:
            try:
                variante = Variante.objects.get(pk=var_id, producto_id=producto.id)
                variante.stock = max(
                    0,
                    _to_int_safe(variante.stock)
                    - _to_int_safe(it.cantidad),
                )
                variante.save(update_fields=["stock"])
            except Exception:
                pass

        producto.stock = max(
            0,
            _to_int_safe(producto.stock) - _to_int_safe(it.cantidad),
        )
        producto.save(update_fields=["stock"])

    pedido.pago_estado = "pagado"
    pedido.save(update_fields=["pago_estado"])


def _enviar_email_confirmacion(pedido: Pedido) -> None:
    """
    Helper antiguo de email de confirmación.
    Ya NO se llama desde estos servicios (lo hace la capa de views),
    pero lo dejo por si en un futuro quieres reutilizarlo.
    """
    moneda = getattr(settings, "MONEDA", "€")
    lineas = "\n".join(
        f"   - {it.titulo} x{it.cantidad} = {it.subtotal} {moneda}"
        for it in pedido.items.all()
    )
    asunto = f"Confirmación de pedido #{pedido.id}"
    cuerpo = (
        f"Hola {pedido.nombre},\n\n"
        f"Gracias por tu compra.\n\n"
        f"Detalles del pedido #{pedido.id}:\n{lineas}\n"
        f"   Envío: {pedido.envio_coste} {moneda}\n"
        f"   Total: {pedido.total} {moneda}\n\n"
        f"Dirección:\n{pedido.direccion}\n{pedido.cp} {pedido.ciudad}\n\n"
        f"Seguimiento: "
        f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}"
        f"/pedidos/seguimiento/{pedido.tracking_token}/\n"
    )
    try:
        send_mail(
            asunto,
            cuerpo,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            [pedido.email],
        )
    except Exception:
        pass

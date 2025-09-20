from decimal import Decimal
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from carrito.cart import Cart
from .models import Pedido, PedidoItem, ShippingMethod


@transaction.atomic
def crear_pedido_desde_carrito(request, datos):
    cart = Cart(request)
    if cart.count() == 0:
        raise ValueError("El carrito está vacío")

    pago_metodo = datos.get("pago_metodo", "contrareembolso")

    pedido = Pedido.objects.create(
        email=datos["email"],
        nombre=datos["nombre"],
        telefono=datos.get("telefono", ""),
        direccion=datos["direccion"],
        ciudad=datos["ciudad"],
        cp=datos["cp"],
        total=Decimal("0.00"),
        pago_metodo=pago_metodo,
        pago_estado="pendiente" if pago_metodo == "contrareembolso" else "iniciado",
    )

    subtotal = Decimal("0.00")
    for item in cart:
        p = item["product"]
        qty = int(item["qty"])

        if p.stock < qty:
            raise ValueError(f"Sin stock suficiente para {p.nombre}")

        if pago_metodo == "contrareembolso":
            p.stock -= qty
            p.save(update_fields=["stock"])

        line_total = Decimal(str(item["subtotal"]))
        PedidoItem.objects.create(
            pedido=pedido,
            producto_id=p.id,
            titulo=p.nombre,
            precio_unit=Decimal(str(item["price"])),
            cantidad=qty,
            subtotal=line_total,
        )
        subtotal += line_total

    # envío
    shipping_cost = Decimal("0.00")
    method = None
    method_id = request.session.get("shipping_method_id")
    if method_id:
        method = ShippingMethod.objects.filter(pk=method_id, activo=True).first()

    ENVIO_GRATIS_DESDE = getattr(settings, "ENVIO_GRATIS_DESDE", Decimal("999999"))
    if subtotal < ENVIO_GRATIS_DESDE and method:
        shipping_cost = Decimal(method.coste)

    pedido.envio_metodo = method
    pedido.envio_coste = shipping_cost
    pedido.total = subtotal + shipping_cost
    pedido.save(update_fields=["envio_metodo", "envio_coste", "total"])

    # limpiar solo en contrareembolso
    if pago_metodo == "contrareembolso":
        try:
            cart.clear()
        except Exception:
            pass
        for k in ("checkout_datos", "checkout_pago", "shipping_method_id"):
            request.session.pop(k, None)

    # email confirmación (solo texto)
    moneda = getattr(settings, "MONEDA", "€")
    lineas = "\n".join(
        f"   - {it.titulo} x{it.cantidad} = {it.subtotal} {moneda}"
        for it in pedido.items.all()
    )
    asunto = f"Confirmación de pedido #{pedido.id}"
    cuerpo = (
        f"Hola {pedido.nombre},\n\n"
        f"Gracias por tu compra en nuestra tienda.\n\n"
        f"Detalles del pedido #{pedido.id}:\n"
        f"{lineas}\n"
        f"   Envío: {pedido.envio_coste} {moneda}\n"
        f"   Total: {pedido.total} {moneda}\n\n"
        f"Dirección de entrega:\n"
        f"{pedido.direccion}\n{pedido.cp} {pedido.ciudad}\n\n"
        f"Seguimiento: {getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/seguimiento/{pedido.tracking_token}/\n"
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

    return pedido


@transaction.atomic
def crear_pedido_tarjeta_pre(request, datos):
    """Crea un pedido preliminar con pago 'tarjeta' y estado 'iniciado' (sin tocar stock)."""
    cart = Cart(request)
    if cart.count() == 0:
        raise ValueError("El carrito está vacío")

    pedido = Pedido.objects.create(
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

    subtotal = Decimal("0.00")
    for item in cart:
        p = item["product"]
        qty = int(item["qty"])
        line_total = Decimal(str(item["subtotal"]))
        PedidoItem.objects.create(
            pedido=pedido,
            producto_id=p.id,
            titulo=p.nombre,
            precio_unit=Decimal(str(item["price"])),
            cantidad=qty,
            subtotal=line_total,
        )
        subtotal += line_total

    shipping_cost = Decimal("0.00")
    method = None
    method_id = request.session.get("shipping_method_id")
    if method_id:
        method = ShippingMethod.objects.filter(pk=method_id, activo=True).first()

    ENVIO_GRATIS_DESDE = getattr(settings, "ENVIO_GRATIS_DESDE", Decimal("999999"))
    if subtotal < ENVIO_GRATIS_DESDE and method:
        shipping_cost = Decimal(method.coste)

    pedido.envio_metodo = method
    pedido.envio_coste = shipping_cost
    pedido.total = subtotal + shipping_cost
    pedido.save(update_fields=["envio_metodo", "envio_coste", "total"])

    return pedido, {"subtotal": subtotal, "shipping_cost": shipping_cost, "total": pedido.total}

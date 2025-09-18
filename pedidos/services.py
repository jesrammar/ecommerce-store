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

    # método de pago recibido desde el paso de pago
    pago_metodo = datos.get("pago_metodo", "contrareembolso")

    # crea el pedido base
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

    # líneas y subtotal
    subtotal = Decimal("0.00")
    for item in cart:
        p = item["product"]
        qty = int(item["qty"])

        if p.stock < qty:
            raise ValueError(f"Sin stock suficiente para {p.nombre}")

        # reducir stock
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
    method = None
    shipping_cost = Decimal("0.00")
    method_id = request.session.get("shipping_method_id")
    if method_id:
        method = ShippingMethod.objects.filter(pk=method_id, activo=True).first()

    ENVIO_GRATIS_DESDE = getattr(settings, "ENVIO_GRATIS_DESDE", Decimal("999999"))
    if subtotal < ENVIO_GRATIS_DESDE and method:
        shipping_cost = Decimal(method.coste)

    # actualizar totales y envío en el pedido
    pedido.envio_metodo = method
    pedido.envio_coste = shipping_cost
    pedido.total = subtotal + shipping_cost
    pedido.save(
        update_fields=[
            "envio_metodo",
            "envio_coste",
            "total",
            "pago_estado",
            "pago_metodo",
        ]
    )

    # (opcional) vaciar carrito
    # cart.clear()

    # --- Enviar email de confirmación ---
    asunto = f"Confirmación de pedido #{pedido.id}"
    cuerpo = (
        f"Hola {pedido.nombre},\n\n"
        f"Gracias por tu compra en nuestra tienda.\n\n"
        f"Detalles del pedido:\n"
        f" - Número de pedido: {pedido.id}\n"
        f" - Método de pago: {pedido.get_pago_metodo_display()}\n"
        f" - Importe total: {pedido.total} €\n"
        f" - Dirección de envío: {pedido.direccion}, {pedido.cp} {pedido.ciudad}\n"
        f" - Método de entrega: {pedido.envio_metodo.nombre if pedido.envio_metodo else 'No seleccionado'}\n"
        f" - Coste de envío: {pedido.envio_coste} €\n\n"
        f"Puedes seguir tu pedido en:\n"
        f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/seguimiento/{pedido.tracking_token}/\n\n"
        f"Un saludo,\nEl equipo de la tienda"
    )
    try:
        send_mail(
            asunto,
            cuerpo,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            [pedido.email],
        )
    except Exception:
        # en dev, mejor no romper el flujo si el mail falla
        pass

    return pedido

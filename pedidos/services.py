from decimal import Decimal
from django.db import transaction
from productos.models import Producto
from carrito.cart import Cart
from .models import Pedido, PedidoItem

@transaction.atomic
def crear_pedido_desde_carrito(request, datos):
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
        pago_estado="pendiente",
    )

    total = Decimal("0.00")
    for item in cart:
        p = item["product"]
        qty = item["qty"]

        if p.stock < qty:
            raise ValueError(f"Sin stock suficiente para {getattr(p, 'nombre', str(p))}")

        p.stock -= qty
        p.save(update_fields=["stock"])

        line_total = item["subtotal"]
        PedidoItem.objects.create(
            pedido=pedido,
            producto_id=p.id,
            titulo=getattr(p, "nombre", str(p)),
            precio_unit=item["price"],
            cantidad=qty,
            subtotal=line_total,
        )
        total += line_total

    pedido.total = total
    pedido.save(update_fields=["total"])
    return pedido

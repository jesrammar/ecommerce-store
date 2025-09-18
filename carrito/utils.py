from decimal import Decimal
from django.conf import settings
from pedidos.models import ShippingMethod

def get_cart(request):
    return request.session.get("cart", {"items": [], "shipping_method": None})

def set_cart(request, cart):
    request.session["cart"] = cart
    request.session.modified = True

def compute_totals(request):
    cart = get_cart(request)
    subtotal = sum(Decimal(str(i["precio"])) * int(i["qty"]) for i in cart.get("items", []))

    method = None
    if cart.get("shipping_method"):
        method = ShippingMethod.objects.filter(pk=cart["shipping_method"], activo=True).first()

    if subtotal >= getattr(settings, "ENVIO_GRATIS_DESDE", Decimal("999999")):
        shipping_cost = Decimal("0.00")
    else:
        shipping_cost = Decimal(method.coste) if method else Decimal("0.00")

    total = subtotal + shipping_cost
    cart.update({
        "subtotal": str(subtotal),
        "shipping_cost": str(shipping_cost),
        "total": str(total),
    })
    set_cart(request, cart)
    return {"subtotal": subtotal, "shipping_cost": shipping_cost, "total": total, "method": method}

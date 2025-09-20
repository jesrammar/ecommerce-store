from carrito.cart import Cart
from django.conf import settings

def globals(request):
    return {
        "ENVIO_GRATIS_DESDE": getattr(settings, "ENVIO_GRATIS_DESDE", 0),
        "MONEDA": getattr(settings, "MONEDA", "€"),
    }

def cart_context(request):
    cart = Cart(request)
    try:
        total = cart.total()
        count = cart.count()
    except Exception:
        total, count = 0, 0
    return {"cart_total": total, "cart_count": count}

from .cart import Cart

def cart_context(request):
    c = Cart(request)
    return {"cart_count": c.count(), "cart_total": c.total()}

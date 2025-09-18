from .cart import Cart
def cart_context(request):
    cart = Cart(request)
    return {"cart_count": cart.count(), "cart_total": cart.total()}

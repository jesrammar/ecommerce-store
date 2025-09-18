from .cart import Cart
from django.utils.functional import cached_property

def cart_context(request):
    cart = request.session.get("cart", {"items": [], "total": 0.0})
    count = sum(item.get("qty", 0) for item in cart.get("items", []))
    return {"cart": cart, "cart_count": count, "cart_total": cart.get("total", 0.0)}




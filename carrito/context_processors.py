# carrito/context_processors.py
from decimal import Decimal
from django.conf import settings

def cart_summary(request):
    """
    Expone en todas las plantillas:
      - cart_count: nº de ítems (sumando cantidades)
      - cart_total: total del carrito
      - MONEDA: símbolo/abreviatura
    """
    cart = request.session.get("cart", {})
    count = 0
    total = Decimal("0.00")
    for item in cart.values():
        qty = int(item.get("qty", 0))
        price = Decimal(str(item.get("price", "0")))
        count += qty
        total += price * qty
    return {
        "cart_count": count,
        "cart_total": total,
        "MONEDA": getattr(settings, "MONEDA", "€"),
    }

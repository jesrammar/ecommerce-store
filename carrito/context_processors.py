from decimal import Decimal, ROUND_HALF_UP

def cart_context(request):
    cart = request.session.get("carrito", {}) or {}
    total = Decimal("0")
    unidades = 0
    for item in cart.values():
        precio = Decimal(str(item.get("precio", "0")))
        cantidad = int(item.get("cantidad", 0))
        total += precio * cantidad
        unidades += cantidad
    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "carrito_unidades": unidades,
        "carrito_total": total,
        "carrito_vacio": unidades == 0,
    }

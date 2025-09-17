from decimal import Decimal

CART_SESSION_ID = "cart"

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if cart is None:
            cart = {}
            self.session[CART_SESSION_ID] = cart
        self.cart = cart

    def add(self, product_id: int, price: str, qty: int = 1, update: bool = False):
        pid = str(product_id)
        if pid not in self.cart:
            self.cart[pid] = {"qty": 0, "price": str(price)}
        self.cart[pid]["qty"] = qty if update else self.cart[pid]["qty"] + qty
        self.save()

    def remove(self, product_id: int):
        pid = str(product_id)
        if pid in self.cart:
            del self.cart[pid]
            self.save()

    def clear(self):
        self.session[CART_SESSION_ID] = {}
        self.session.modified = True

    def __iter__(self):
        from productos.models import Producto
        product_ids = list(self.cart.keys())
        productos = {str(p.id): p for p in Producto.objects.filter(id__in=product_ids)}
        for pid, item in self.cart.items():
            p = productos.get(pid)
            if not p:
                continue
            yield {
                "product": p,
                "qty": item["qty"],
                "price": Decimal(item["price"]),
                "subtotal": Decimal(item["price"]) * item["qty"],
            }

    def count(self) -> int:
        return sum(item["qty"] for item in self.cart.values())

    def total(self) -> Decimal:
        return sum(Decimal(i["price"]) * i["qty"] for i in self.cart.values())

    def save(self):
        self.session.modified = True

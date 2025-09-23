from decimal import Decimal
from django.conf import settings
from productos.models import Producto

CART_SESSION_ID = "cart"

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    # item structure en session:
    # { str(product_id): {"qty": int, "price": "9.99"} }

    def add(self, product: Producto, qty=1, replace=False):
        pid = str(product.id)
        price = str(product.precio)  # guardamos como string para serialize
        if pid not in self.cart:
            self.cart[pid] = {"qty": 0, "price": price}
        if replace:
            self.cart[pid]["qty"] = max(0, int(qty))
        else:
            self.cart[pid]["qty"] = max(0, self.cart[pid]["qty"] + int(qty))
        if self.cart[pid]["qty"] <= 0:
            del self.cart[pid]
        self._save()

    def remove(self, product: Producto):
        pid = str(product.id)
        if pid in self.cart:
            del self.cart[pid]
            self._save()

    def clear(self):
        self.session[CART_SESSION_ID] = {}
        self._save()

    def _save(self):
        self.session.modified = True

    def __len__(self):
        return sum(item["qty"] for item in self.cart.values())

    def count(self):
        return len(self)

    def total(self):
        return sum(Decimal(i["price"]) * i["qty"] for i in self.cart.values())

    def __iter__(self):
        pids = self.cart.keys()
        products = Producto.objects.filter(id__in=pids)
        cart_copy = self.cart.copy()
        for p in products:
            item = cart_copy[str(p.id)]
            item["product"] = p
            item["price"] = Decimal(item["price"])
            item["subtotal"] = item["price"] * item["qty"]
            yield item

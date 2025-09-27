from decimal import Decimal
import json
from productos.models import Producto

CART_SESSION_ID = "cart"

def _to_dict(value):
    """Convierte JSON string -> dict de forma segura."""
    if isinstance(value, dict) or value is None:
        return value or {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if cart is None:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def save(self):
        self.session[CART_SESSION_ID] = self.cart
        self.session.modified = True

    def add(self, product, quantity=1, override=False, meta_json=None):
        pid = str(product.id)
        meta_dict = _to_dict(meta_json)

        if pid not in self.cart:
            self.cart[pid] = {
                "qty": 0,
                "price": str(product.precio),
                "meta": meta_dict,
                "name": product.nombre,
                "slug": product.slug,
            }

        if override:
            self.cart[pid]["qty"] = int(quantity)
        else:
            self.cart[pid]["qty"] += int(quantity)

        # por si actualizas personalización/variantes
        if meta_json is not None:
            self.cart[pid]["meta"] = meta_dict

        self.save()

    def remove(self, product_id):
        pid = str(getattr(product_id, "id", product_id))
        if pid in self.cart:
            del self.cart[pid]
            self.save()

    def clear(self):
        self.session.pop(CART_SESSION_ID, None)
        self.session.modified = True

    def __iter__(self):
        ids = [int(pid) for pid in self.cart.keys()]
        productos = {p.id: p for p in Producto.objects.filter(id__in=ids)}
        for pid, raw in self.cart.items():
            pid_int = int(pid)
            product = productos.get(pid_int)
            price = Decimal(str(raw.get("price", "0")))
            qty = int(raw.get("qty", 0))
            meta = _to_dict(raw.get("meta"))
            yield {
                "product": product,
                "product_id": pid_int,
                "qty": qty,
                "price": price,
                "subtotal": price * qty,
                "meta": meta,
                "name": raw.get("name", ""),
                "slug": raw.get("slug", ""),
            }

    def __len__(self):
        return sum(int(i["qty"]) for i in self.cart.values())

    def count(self):
        return self.__len__()

    @property
    def total(self):
        return sum(Decimal(str(i["price"])) * int(i["qty"]) for i in self.cart.values())

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

    def add(self, product, quantity=1, override=False, meta_json=None, unit_price=None):
        """
        Añade o actualiza un producto en el carrito.

        - product: instancia de Producto
        - quantity: cantidad a añadir
        - override: si True, se fija la cantidad; si False, se suma
        - meta_json: JSON con info extra (variante, personalización, etc.)
        - unit_price: precio unitario final (producto + variante + personalización).
                      Si no se pasa, se usa product.precio.
        """
        pid = str(product.id)
        meta_dict = _to_dict(meta_json)

        # Recuperar o crear la fila
        row = self.cart.get(pid)
        if row is None:
            base_price = unit_price if unit_price is not None else getattr(product, "precio", 0)
            row = {
                "qty": 0,
                "price": str(base_price),
                "meta": meta_dict,
                "name": product.nombre,
                "slug": product.slug,
            }

        # Actualizar cantidad
        if override:
            row["qty"] = int(quantity)
        else:
            row["qty"] = int(row.get("qty", 0)) + int(quantity)

        # Actualizar meta si nos llega nueva
        if meta_json is not None:
            row["meta"] = meta_dict

        # Actualizar precio solo si nos pasan uno calculado
        if unit_price is not None:
            row["price"] = str(unit_price)

        # Aseguramos que siempre haya un precio coherente
        if "price" not in row:
            row["price"] = str(getattr(product, "precio", 0))

        self.cart[pid] = row
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

    def get_quantity(self, product_id: int) -> int:
        """Cantidad actual de un producto en el carrito."""
        return int(self.cart.get(str(product_id), {}).get("qty", 0))

    def set(self, product, quantity: int, meta_json=None):
        """
        Fija la cantidad exacta de un producto (sirve para 'Actualizar').
        Usa también para recortar al stock cuando haga falta.
        """
        pid = str(getattr(product, "id", product))
        meta_dict = _to_dict(meta_json)
        q = int(max(0, quantity))

        if q == 0:
            if pid in self.cart:
                del self.cart[pid]
        else:
            row = self.cart.get(pid, {})
            row.update({
                "qty": q,
                "price": row.get("price", str(getattr(product, "precio", "0"))),
                "name": row.get("name", getattr(product, "nombre", "")),
                "slug": row.get("slug", getattr(product, "slug", "")),
                "meta": meta_dict or row.get("meta", {}),
            })
            self.cart[pid] = row

        self.save()

    # --- NUEVO ---
    def stock_errors(self):
        """
        Devuelve una lista de dicts con líneas que superan el stock:
        [{ 'product': <Producto>, 'qty': 7, 'disponible': 1 }, ...]
        """
        errores = []
        ids = [int(pid) for pid in self.cart.keys()]
        productos = {p.id: p for p in Producto.objects.filter(id__in=ids)}
        for pid, raw in self.cart.items():
            p = productos.get(int(pid))
            qty = int(raw.get("qty", 0))
            disp = int(getattr(p, "stock", 0)) if p else 0
            if qty > disp:
                errores.append({"product": p, "qty": qty, "disponible": disp})
        return errores

    def has_stock_errors(self) -> bool:
        """True si alguna línea del carrito excede el stock."""
        return bool(self.stock_errors())

    def normalize_to_stock(self) -> int:
        """
        Recorta automáticamente cantidades al stock disponible.
        Devuelve cuántas líneas fueron ajustadas (para mostrar aviso).
        """
        ajustadas = 0
        ids = [int(pid) for pid in self.cart.keys()]
        productos = {p.id: p for p in Producto.objects.filter(id__in=ids)}
        for pid, raw in list(self.cart.items()):
            p = productos.get(int(pid))
            if not p:
                del self.cart[pid]
                ajustadas += 1
                continue
            qty = int(raw.get("qty", 0))
            disp = int(getattr(p, "stock", 0))
            if disp <= 0:
                del self.cart[pid]
                ajustadas += 1
            elif qty > disp:
                raw["qty"] = disp
                self.cart[pid] = raw
                ajustadas += 1
        if ajustadas:
            self.save()
        return ajustadas

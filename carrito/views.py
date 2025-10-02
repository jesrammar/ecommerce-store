from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from carrito.cart import Cart
from productos.models import Producto


def _to_int_safe(v, default=1, min_val=0):
    try:
        s = str(v).strip()
        if not s:
            return default
        return max(min_val, int(s))
    except Exception:
        return default


@require_http_methods(["GET"])
def carrito_ver(request):
    cart = Cart(request)
    return render(request, "carrito/ver.html", {"cart": cart, "stock_errores": cart.stock_errors()})



@require_POST
def carrito_add(request, product_id: int):
    """
    Añade respetando el stock disponible restante (stock - ya_en_carrito).
    Si se excede, ajusta y avisa. Nunca permite superar el stock.
    """
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id, activo=True)

    q = request.POST.get("quantity") or request.POST.get("qty") or request.POST.get("cantidad") or "1"
    quantity = _to_int_safe(q, default=1, min_val=1)

    # Cantidad ya en carrito para este producto
    if hasattr(cart, "get_quantity"):
        ya = cart.get_quantity(product.id)
    else:
        # Fallback si no existe get_quantity
        ya = 0
        for it in cart:
            if getattr(it, "product_id", None) == product.id or getattr(it, "product", None) and it["product"].id == product.id:
                ya = it["qty"]
                break

    max_add = max(int(product.stock) - int(ya), 0)

    if max_add <= 0:
        messages.error(request, f"No queda stock para {product.nombre}.")
        return redirect("carrito:carrito_ver")

    if quantity > max_add:
        # Ajuste al máximo posible
        nuevo_total = ya + max_add
        if hasattr(cart, "set"):
            cart.set(product, nuevo_total)
        else:
            cart.add(product=product, quantity=nuevo_total, override=True if "override" in Cart.add.__code__.co_varnames else False)
        messages.warning(request, f"Solo quedaban {max_add} uds de {product.nombre}. Ajustamos tu carrito.")
    else:
        # Añadido normal
        kwargs = {"product": product, "quantity": quantity}
        if "override_quantity" in Cart.add.__code__.co_varnames:
            kwargs["override_quantity"] = False
        elif "override" in Cart.add.__code__.co_varnames:
            kwargs["override"] = False
        cart.add(**kwargs)
        messages.success(request, "Producto añadido al carrito.")

    return redirect("carrito:carrito_ver")


@require_POST
def carrito_update(request, product_id: int):
    """
    Actualiza la cantidad y la TOPA al stock. Si piden 0, elimina.
    """
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id, activo=True)

    q = request.POST.get("quantity") or request.POST.get("qty") or request.POST.get("cantidad") or "1"
    quantity = _to_int_safe(q, default=1, min_val=0)

    if quantity == 0:
        # Eliminar línea
        if hasattr(cart, "remove"):
            cart.remove(product)
        else:
            cart.add(product=product, quantity=0, override=True if "override" in Cart.add.__code__.co_varnames else False)
        messages.info(request, f"Quitado {product.nombre}.")
        return redirect("carrito:carrito_ver")

    max_qty = int(product.stock)
    new_qty = min(quantity, max_qty)

    # Aplicar cantidad (capada si hace falta)
    if hasattr(cart, "set"):
        cart.set(product, new_qty)
    else:
        cart.add(product=product, quantity=new_qty, override=True if "override" in Cart.add.__code__.co_varnames else False)

    if new_qty < quantity:
        messages.error(request, f"Sin stock suficiente para {product.nombre}. Ajustado a {new_qty}.")
    else:
        messages.success(request, "Cantidad actualizada.")
    return redirect("carrito:carrito_ver")


@require_POST
def carrito_remove(request, product_id: int):
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id)
    if hasattr(cart, "remove"):
        cart.remove(product)
    else:
        cart.add(product=product, quantity=0, override=True if "override" in Cart.add.__code__.co_varnames else False)
    messages.info(request, "Producto eliminado.")
    return redirect("carrito:carrito_ver")


@require_POST
def carrito_clear(request):
    cart = Cart(request)
    if hasattr(cart, "clear"):
        cart.clear()
    else:
        request.session.pop(getattr(cart, "session_key", "cart"), None)
        request.session.modified = True
    messages.info(request, "Carrito vaciado.")
    return redirect("carrito:carrito_ver")

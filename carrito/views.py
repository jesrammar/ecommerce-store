from __future__ import annotations
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods
from carrito.cart import Cart
from productos.models import Producto

def _to_int_safe(v, default=1):
    try:
        s = str(v).strip()
        return max(1, int(s)) if s else default
    except Exception:
        return default

@require_http_methods(["GET"])
def carrito_ver(request):
    return render(request, "carrito/ver.html", {"cart": Cart(request)})

@require_POST
def carrito_add(request, product_id: int):
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id)
    q = request.POST.get("quantity") or request.POST.get("qty") or request.POST.get("cantidad") or "1"
    quantity = _to_int_safe(q, 1)
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
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id)
    q = request.POST.get("quantity") or request.POST.get("qty") or request.POST.get("cantidad") or "1"
    quantity = _to_int_safe(q, 1)
    kwargs = {"product": product, "quantity": quantity}
    if "override_quantity" in Cart.add.__code__.co_varnames:
        kwargs["override_quantity"] = True
    elif "override" in Cart.add.__code__.co_varnames:
        kwargs["override"] = True
    cart.add(**kwargs)
    messages.success(request, "Cantidad actualizada.")
    return redirect("carrito:carrito_ver")

@require_POST
def carrito_remove(request, product_id: int):
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id)
    if hasattr(cart, "remove"):
        cart.remove(product)
    else:
        kwargs = {"product": product, "quantity": 0}
        if "override_quantity" in Cart.add.__code__.co_varnames:
            kwargs["override_quantity"] = True
        elif "override" in Cart.add.__code__.co_varnames:
            kwargs["override"] = True
        cart.add(**kwargs)
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

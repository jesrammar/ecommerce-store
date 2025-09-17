from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from productos.models import Producto
from .cart import Cart

def ver_carrito(request):
    return render(request, "carrito/ver.html", {"cart": Cart(request)})

@require_POST
def add(request, pid):
    cart = Cart(request)
    p = get_object_or_404(Producto, id=pid, activo=True)
    qty = max(1, int(request.POST.get("qty", 1)))
    if p.stock >= qty:
        cart.add(product_id=p.id, price=str(p.precio), qty=qty)
    return redirect(request.POST.get("next") or "carrito_ver")

@require_POST
def update(request, pid):
    cart = Cart(request)
    p = get_object_or_404(Producto, id=pid, activo=True)
    qty = max(0, int(request.POST.get("qty", 1)))
    if qty == 0:
        cart.remove(p.id)
    else:
        qty = min(qty, p.stock)
        cart.add(product_id=p.id, price=str(p.precio), qty=qty, update=True)
    return redirect("carrito_ver")

def remove(request, pid):
    Cart(request).remove(pid)
    return redirect("carrito_ver")

def clear(request):
    Cart(request).clear()
    return redirect("carrito_ver")

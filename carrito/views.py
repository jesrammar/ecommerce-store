from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from productos.models import Producto
from .cart import Cart
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ShippingSelectForm
from .utils import get_cart, set_cart, compute_totals
from decimal import Decimal
from django.conf import settings
from pedidos.models import ShippingMethod



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


def seleccionar_envio(request):
    # guardamos solo el id en sesión para no tocar tu Cart
    if request.method == "POST":
        form = ShippingSelectForm(request.POST)
        if form.is_valid():
            request.session["shipping_method_id"] = form.cleaned_data["shipping_method"].id
            request.session.modified = True
            messages.success(request, "Método de entrega actualizado.")
            return redirect("carrito:carrito_ver")
    else:
        initial = {"shipping_method": request.session.get("shipping_method_id")}
        form = ShippingSelectForm(initial=initial)
    return render(request, "carrito/seleccionar_envio.html", {"form": form})



def ver_carrito(request):
    cart = Cart(request)
    subtotal = cart.total()
    method = None
    shipping_cost = Decimal("0.00")

    method_id = request.session.get("shipping_method_id")
    if method_id:
        method = ShippingMethod.objects.filter(pk=method_id, activo=True).first()

    ENVIO_GRATIS_DESDE = getattr(settings, "ENVIO_GRATIS_DESDE", Decimal("999999"))
    if subtotal >= ENVIO_GRATIS_DESDE:
        shipping_cost = Decimal("0.00")
    else:
        shipping_cost = Decimal(getattr(method, "coste", 0) or 0)

    total = subtotal + shipping_cost
    ctx = {
        "cart": cart,
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "shipping_method": method,
        "total": total,
    }
    return render(request, "carrito/ver.html", ctx)


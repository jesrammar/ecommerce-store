from decimal import Decimal
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from productos.models import Producto
from .cart import Cart

def carrito_ver(request):
    cart = Cart(request)
    return render(request, "carrito/ver.html", {"cart": cart})

@require_POST
def carrito_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id, activo=True)
    try:
        qty = int(request.POST.get("qty", 1))
    except Exception:
        qty = 1
    if qty < 1:
        qty = 1

    # control stock
    if product.stock < qty + sum(
        i["qty"] for i in request.session.get("cart", {}).values()
        if str(product.id) in request.session.get("cart", {})
    ):
        messages.warning(request, f"No hay stock suficiente para {product.nombre}.")
        return redirect(request.META.get("HTTP_REFERER", reverse("carrito:carrito_ver")))

    cart.add(product, qty=qty, replace=False)
    messages.success(request, f"“{product.nombre}” añadido al carrito.")
    return redirect(request.META.get("HTTP_REFERER", reverse("carrito:carrito_ver")))

@require_POST
def carrito_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id)
    try:
        qty = int(request.POST.get("qty", 1))
    except Exception:
        qty = 1
    qty = max(0, qty)

    if qty > product.stock:
        messages.warning(request, f"Stock máximo disponible: {product.stock}.")
        qty = product.stock

    cart.add(product, qty=qty, replace=True)
    messages.info(request, f"Cantidad actualizada para “{product.nombre}”.")
    return redirect("carrito:carrito_ver")

def carrito_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Producto, pk=product_id)
    cart.remove(product)
    messages.info(request, f"“{product.nombre}” eliminado del carrito.")
    return redirect("carrito:carrito_ver")

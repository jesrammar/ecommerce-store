from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from productos.models import Producto
from pedidos.models import ShippingMethod
from .cart import Cart


@require_POST
def add(request, pid):
    cart = Cart(request)
    p = get_object_or_404(Producto, id=pid, activo=True)
    qty = max(1, int(request.POST.get("qty", 1)))
    if p.stock >= qty:
        cart.add(product_id=p.id, price=str(p.precio), qty=qty)
    return redirect(request.POST.get("next") or "carrito:carrito_ver")


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
    return redirect("carrito:carrito_ver")


def remove(request, pid):
    Cart(request).remove(pid)
    return redirect("carrito:carrito_ver")


def clear(request):
    Cart(request).clear()
    return redirect("carrito:carrito_ver")


def seleccionar_envio(request):
    """
    Vista simple para seleccionar el método de envío y guardarlo en sesión.
    Si prefieres hacerlo dentro de la propia vista del carrito, puedes
    postear directamente a esta URL desde el template del carrito.
    """
    if request.method == "POST":
        sm_id = request.POST.get("shipping_method_id")
        if sm_id and ShippingMethod.objects.filter(pk=sm_id, activo=True).exists():
            request.session["shipping_method_id"] = int(sm_id)
            request.session.modified = True
            messages.success(request, "Método de entrega actualizado.")
        else:
            messages.error(request, "Método de entrega no válido.")
        return redirect("carrito:carrito_ver")

    # GET: pintar un selector muy básico
    metodos = ShippingMethod.objects.filter(activo=True).order_by("orden", "id")
    seleccionado = request.session.get("shipping_method_id")
    return render(
        request,
        "carrito/seleccionar_envio.html",
        {"metodos": metodos, "seleccionado": int(seleccionado) if seleccionado else None},
    )

def ver_carrito(request):
    cart = Cart(request)
    subtotal = Decimal(str(cart.total()))

    # método de envío seleccionado en sesión
    selected_id = request.session.get("shipping_method_id")
    shipping_method = None
    shipping_cost = Decimal("0.00")

    if selected_id:
        shipping_method = ShippingMethod.objects.filter(pk=selected_id, activo=True).first()

    ENVIO_GRATIS_DESDE = getattr(settings, "ENVIO_GRATIS_DESDE", Decimal("999999"))
    if subtotal < ENVIO_GRATIS_DESDE and shipping_method:
        shipping_cost = Decimal(shipping_method.coste)

    total = subtotal + shipping_cost

    ctx = {
        "cart": cart,
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "shipping_method": shipping_method,
        "shipping_methods": ShippingMethod.objects.filter(activo=True).order_by("orden", "id"),
        "shipping_selected_id": int(selected_id) if selected_id else None,
        "ENVIO_GRATIS_DESDE": ENVIO_GRATIS_DESDE,
        "total": total,
    }
    return render(request, "carrito/ver.html", ctx)
from __future__ import annotations

import json  # <-- NUEVO

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from carrito.cart import Cart
from productos.models import Producto, Variante  # <-- AÑADIMOS Variante


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

    AHORA:
    - Lee variante seleccionada (campo 'variante')
    - Lee personalización (texto / color_texto / meta_json)
    - Calcula precio unitario final con Producto.calcular_precio
    - Lo pasa a Cart.add(..., unit_price=...)
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
       
        nuevo_total = ya + max_add
        if hasattr(cart, "set"):
            cart.set(product, nuevo_total)
        else:
            cart.add(
                product=product,
                quantity=nuevo_total,
                override=True if "override" in Cart.add.__code__.co_varnames else False,
            )
        messages.warning(request, f"Solo quedaban {max_add} uds de {product.nombre}. Ajustamos tu carrito.")
    else:
    
        raw_meta = request.POST.get("meta_json") or "{}"
        try:
            meta = json.loads(raw_meta)
        except Exception:
            meta = {}

        # 2) VARIANTE (talla / color)
        variante_obj = None

        # a) si viene un id de variante desde el formulario
        variante_id = request.POST.get("variante") or meta.get("variante_id")
        if variante_id:
            try:
                variante_obj = Variante.objects.get(pk=variante_id, producto=product)
            except Variante.DoesNotExist:
                variante_obj = None

        # b) guardar info básica de variante en meta
        if variante_obj:
            meta["variante_id"] = variante_obj.id
            meta["talla"] = variante_obj.talla
            meta["color"] = variante_obj.color

        # 3) PERSONALIZACIÓN
        pers = meta.get("personalizacion") or {}

        # Si no viene en meta, intentamos construirla desde el formulario
        if not pers:
            texto = request.POST.get("texto") or ""
            color_texto = request.POST.get("color_texto") or ""
            if texto or color_texto:
                pers = {
                    "texto": texto,
                    "color_texto": color_texto,
                    # preview_url la rellenará el endpoint de preview, si lo usas
                }

        if pers:
            meta["personalizacion"] = pers

        # 4) Calcular precio final
        unit_price = product.calcular_precio(variante=variante_obj, personalizacion=pers)

        # 5) Guardar meta como JSON para el carrito
        meta_json = json.dumps(meta)

        # 6) Llamar a cart.add con unit_price + meta_json
        kwargs = {
            "product": product,
            "quantity": quantity,
            "meta_json": meta_json,
            "unit_price": unit_price,
        }
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
    (No toca variantes ni personalización, solo cantidad.)
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
            cart.add(
                product=product,
                quantity=0,
                override=True if "override" in Cart.add.__code__.co_varnames else False,
            )
        messages.info(request, f"Quitado {product.nombre}.")
        return redirect("carrito:carrito_ver")

    max_qty = int(product.stock)
    new_qty = min(quantity, max_qty)

    # Aplicar cantidad (capada si hace falta)
    if hasattr(cart, "set"):
        cart.set(product, new_qty)
    else:
        cart.add(
            product=product,
            quantity=new_qty,
            override=True if "override" in Cart.add.__code__.co_varnames else False,
        )

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
        cart.add(
            product=product,
            quantity=0,
            override=True if "override" in Cart.add.__code__.co_varnames else False,
        )
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

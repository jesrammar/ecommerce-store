from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest
from decimal import Decimal
import stripe

from .forms import DatosEnvioForm, MetodoPagoForm
from .services import crear_pedido_desde_carrito, crear_pedido_tarjeta_pre
from .models import Pedido
from productos.models import Producto
from carrito.cart import Cart


# ---------- Paso 1: datos envío ----------
def checkout_datos(request):
    if request.method == "POST":
        form = DatosEnvioForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # ⚠️ Importante: guarda SOLO IDs de método de envío en sesión, no objetos
            shipping_method = data.get("envio_metodo")
            if shipping_method:
                request.session["shipping_method_id"] = shipping_method.id

            # Guarda datos del cliente
            request.session["checkout_datos"] = {
                "email": data["email"],
                "nombre": data["nombre"],
                "telefono": data.get("telefono", ""),
                "direccion": data["direccion"],
                "ciudad": data["ciudad"],
                "cp": data["cp"],
            }
            request.session.modified = True
            return redirect("pedidos:checkout_pago")
    else:
        initial = request.session.get("checkout_datos", {})
        form = DatosEnvioForm(initial=initial)

    return render(request, "pedidos/checkout_datos.html", {"form": form})


# ---------- Paso 2: seleccionar método de pago ----------
def checkout_pago(request):
    datos_cliente = request.session.get("checkout_datos")
    if not datos_cliente:
        messages.error(request, "Completa primero tus datos de entrega.")
        return redirect("pedidos:checkout_datos")

    if request.method == "POST":
        form = MetodoPagoForm(request.POST)
        if form.is_valid():
            request.session["checkout_pago"] = {"pago_metodo": form.cleaned_data["pago_metodo"]}
            request.session.modified = True

            if form.cleaned_data["pago_metodo"] == "contrareembolso":
                # Crear pedido y finalizar
                pedido = crear_pedido_desde_carrito(request, {**datos_cliente, **request.session.get("checkout_pago", {})})
                # Limpiar
                for k in ("checkout_datos", "checkout_pago", "shipping_method_id"):
                    request.session.pop(k, None)
                return redirect("pedidos:checkout_ok", pedido_id=pedido.id)
            else:
                return redirect("pedidos:checkout_tarjeta")
    else:
        initial = request.session.get("checkout_pago") or {}
        form = MetodoPagoForm(initial=initial)

    # Aviso si faltan claves de Stripe
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PUBLIC_KEY:
        messages.warning(request, "Pago con tarjeta no disponible: falta configuración de Stripe.")

    return render(request, "pedidos/checkout_pago.html", {"form": form})


# ---------- Stripe Checkout ----------
def checkout_tarjeta(request):
    datos_cliente = request.session.get("checkout_datos")
    pago = request.session.get("checkout_pago")

    if not datos_cliente or not pago or pago.get("pago_metodo") != "tarjeta":
        messages.error(request, "Selecciona tarjeta en el paso anterior.")
        return redirect("pedidos:checkout_pago")

    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PUBLIC_KEY:
        messages.error(request, "Stripe no está configurado (claves ausentes).")
        return redirect("pedidos:checkout_pago")

    # Crea pedido preliminar (sin tocar stock)
    pedido, totals = crear_pedido_tarjeta_pre(request, {**datos_cliente, **pago})

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Construir líneas para Stripe en céntimos
    line_items = []
    for it in pedido.items.all():
        unit_amount = int(Decimal(it.precio_unit) * 100)
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": it.titulo},
                "unit_amount": unit_amount,
            },
            "quantity": it.cantidad,
        })

    if pedido.envio_coste and Decimal(pedido.envio_coste) > 0:
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": f"Envío ({pedido.envio_metodo.nombre})" if pedido.envio_metodo else "Envío"},
                "unit_amount": int(Decimal(pedido.envio_coste) * 100),
            },
            "quantity": 1,
        })

    success_url = request.build_absolute_uri(
        reverse("pedidos:checkout_ok", kwargs={"pedido_id": pedido.id})
    )
    cancel_url = request.build_absolute_uri(reverse("pedidos:checkout_pago"))

    session = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=line_items,
        customer_email=pedido.email,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"pedido_id": str(pedido.id)},
    )

    pedido.pago_ref = session.id
    pedido.save(update_fields=["pago_ref"])

    return render(
        request,
        "pedidos/checkout_tarjeta.html",
        {"session_id": session.id, "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY, "pedido": pedido},
    )


# ---------- Webhook de Stripe ----------
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception:
        return HttpResponseBadRequest("Invalid payload or signature")

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        pedido_id = (session.get("metadata") or {}).get("pedido_id")
        payment_intent = session.get("payment_intent") or session.get("id")

        if pedido_id:
            try:
                pedido = Pedido.objects.prefetch_related("items").get(pk=int(pedido_id))
            except Pedido.DoesNotExist:
                return HttpResponse(status=200)

            if pedido.pago_estado != "pagado":
                pedido.pago_estado = "pagado"
                pedido.pago_ref = payment_intent
                pedido.save(update_fields=["pago_estado", "pago_ref"])

                # Descontar stock
                for it in pedido.items.all():
                    try:
                        p = Producto.objects.get(pk=it.producto_id)
                        p.stock = max(0, p.stock - it.cantidad)
                        p.save(update_fields=["stock"])
                    except Producto.DoesNotExist:
                        pass
    return HttpResponse(status=200)


# ---------- Paso 3 OK ----------
def checkout_ok(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    # Si fue tarjeta y ya está pagado, limpiar carrito/sesión
    if pedido.pago_metodo == "tarjeta" and pedido.pago_estado == "pagado":
        try:
            Cart(request).clear()
        except Exception:
            pass
        for k in ("checkout_datos", "checkout_pago", "shipping_method_id"):
            request.session.pop(k, None)

    return render(request, "pedidos/checkout_ok.html", {"pedido": pedido})


# ---------- Seguimiento ----------
def seguimiento(request, token):
    pedido = get_object_or_404(Pedido, tracking_token=token)
    return render(request, "pedidos/seguimiento.html", {"pedido": pedido})

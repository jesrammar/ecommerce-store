# pedidos/views.py
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
from .models import Pedido, ShippingMethod
from carrito.cart import Cart

# Paso 1: datos cliente + envío
def checkout_datos(request):
    if request.method == "POST":
        form = DatosEnvioForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # persistimos datos + método de envío elegido
            request.session["checkout_datos"] = {
                "nombre": cd["nombre"],
                "email": cd["email"],
                "telefono": cd.get("telefono", ""),
                "direccion": cd["direccion"],
                "ciudad": cd["ciudad"],
                "cp": cd["cp"],
            }
            request.session["shipping_method_id"] = cd["envio_metodo"].id
            request.session.modified = True
            return redirect("pedidos:checkout_pago")
    else:
        initial = request.session.get("checkout_datos", {}).copy()
        # preseleccionar envío previo si lo hubiera
        sm_id = request.session.get("shipping_method_id")
        if sm_id:
            try:
                initial["envio_metodo"] = ShippingMethod.objects.get(pk=sm_id, activo=True)
            except ShippingMethod.DoesNotExist:
                pass
        form = DatosEnvioForm(initial=initial)

    return render(request, "pedidos/checkout_datos.html", {"form": form})

# Paso 2: método de pago
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
                datos = {**datos_cliente, **request.session.get("checkout_pago", {})}
                pedido = crear_pedido_desde_carrito(request, datos)
                messages.success(request, f"Pedido #{pedido.id} creado correctamente.")
                return redirect("pedidos:checkout_ok", pedido_id=pedido.id)
            else:
                # si stripe no está configurado aún, muestra aviso
                if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PUBLIC_KEY:
                    messages.error(request, "Pago con tarjeta no disponible: falta configuración de Stripe.")
                    return redirect("pedidos:checkout_pago")
                return redirect("pedidos:checkout_tarjeta")
    else:
        initial = (request.session.get("checkout_pago") or {}).copy()
        form = MetodoPagoForm(initial=initial)

    return render(request, "pedidos/checkout_pago.html", {"form": form})

# Tarjeta (Stripe Checkout) - placeholder si aún no quieres probar Stripe
def checkout_tarjeta(request):
    datos_cliente = request.session.get("checkout_datos")
    pago = request.session.get("checkout_pago")
    if not datos_cliente or not pago or pago.get("pago_metodo") != "tarjeta":
        messages.error(request, "Selecciona tarjeta en el paso anterior.")
        return redirect("pedidos:checkout_pago")

    # Crear pedido preliminar (sin restar stock todavía)
    pedido, totals = crear_pedido_tarjeta_pre(request, {**datos_cliente, **pago})

    # Si no quieres integrar Stripe aún, muestra pantalla con resumen:
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PUBLIC_KEY:
        return render(request, "pedidos/checkout_tarjeta.html", {
            "pedido": pedido,
            "session_id": None,
            "STRIPE_PUBLIC_KEY": "",
            "modo_demo": True,
        })

    # Stripe Checkout real
    stripe.api_key = settings.STRIPE_SECRET_KEY
    line_items = []
    for it in pedido.items.all():
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": it.titulo},
                "unit_amount": int(Decimal(it.precio_unit) * 100),
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

    success_url = request.build_absolute_uri(reverse("pedidos:checkout_ok", kwargs={"pedido_id": pedido.id}))
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

    return render(request, "pedidos/checkout_tarjeta.html", {
        "session_id": session.id,
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
        "pedido": pedido,
        "modo_demo": False,
    })

# Webhook (si activas Stripe)
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
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
                # Descontar stock aquí (tarjeta)
                for it in pedido.items.all():
                    try:
                        p = it  # placeholder, lo haces con tu modelo Producto si quieres
                    except Exception:
                        pass
    return HttpResponse(status=200)

# Paso 3: confirmación OK
def checkout_ok(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    # Si tarjeta pagada, limpia carrito y sesión
    if pedido.pago_metodo == "tarjeta" and pedido.pago_estado == "pagado":
        try:
            Cart(request).clear()
        except Exception:
            pass
        for k in ("checkout_datos","checkout_pago","shipping_method_id"):
            request.session.pop(k, None)
    return render(request, "pedidos/checkout_ok.html", {"pedido": pedido})

# Seguimiento por token público
def seguimiento(request, token):
    pedido = get_object_or_404(Pedido, tracking_token=token)
    return render(request, "pedidos/seguimiento.html", {"pedido": pedido})

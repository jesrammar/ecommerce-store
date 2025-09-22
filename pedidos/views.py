from decimal import Decimal
import stripe

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail  # si usas el HTML, cambia a EmailMultiAlternatives
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from carrito.cart import Cart
from productos.models import Producto
from .forms import DatosEnvioForm, MetodoPagoForm
from .models import Pedido
from .services import crear_pedido_desde_carrito, crear_pedido_tarjeta_pre


# ---------- Paso 1: datos de envío ----------
def checkout_datos(request):
    if request.method == "POST":
        form = DatosEnvioForm(request.POST)
        if form.is_valid():
            request.session["checkout_datos"] = form.cleaned_data
            return redirect("pedidos:checkout_pago")
    else:
        form = DatosEnvioForm(initial=request.session.get("checkout_datos", {}))
    return render(request, "pedidos/checkout_datos.html", {"form": form})


# ---------- Paso 2: método de pago ----------
def checkout_pago(request):
    datos_cliente = request.session.get("checkout_datos")
    if not datos_cliente:
        messages.error(request, "Completa primero tus datos de entrega.")
        return redirect("pedidos:checkout_datos")

    if request.method == "POST":
        form = MetodoPagoForm(request.POST)
        if form.is_valid():
            pago_metodo = form.cleaned_data["pago_metodo"]
            request.session["checkout_pago"] = {"pago_metodo": pago_metodo}
            request.session.modified = True

            if pago_metodo == "contrareembolso":
                # Creamos pedido y limpiamos carrito (compra rápida)
                pedido = crear_pedido_desde_carrito(request, {**datos_cliente, "pago_metodo": "contrareembolso"})
                try:
                    Cart(request).clear()
                except Exception:
                    pass
                for k in ("checkout_datos", "checkout_pago", "shipping_method_id"):
                    request.session.pop(k, None)
                return redirect("pedidos:checkout_ok", pedido_id=pedido.id)

            # Tarjeta
            return redirect("pedidos:checkout_tarjeta")
    else:
        initial = (request.session.get("checkout_pago") or {}).copy()
        form = MetodoPagoForm(initial=initial)

    return render(request, "pedidos/checkout_pago.html", {"form": form})


# ---------- Tarjeta (Stripe Checkout) ----------
def checkout_tarjeta(request):
    datos_cliente = request.session.get("checkout_datos")
    pago = request.session.get("checkout_pago")
    if not datos_cliente or not pago or pago.get("pago_metodo") != "tarjeta":
        messages.error(request, "Selecciona tarjeta en el paso anterior.")
        return redirect("pedidos:checkout_pago")

    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PUBLIC_KEY:
        messages.error(request, "Pago con tarjeta no disponible: falta configuración de Stripe.")
        return redirect("pedidos:checkout_pago")

    pedido, _totals = crear_pedido_tarjeta_pre(request, {**datos_cliente, **pago})
    stripe.api_key = settings.STRIPE_SECRET_KEY

    line_items = []
    for it in pedido.items.all():
        # it.precio_unit es Decimal -> centimos
        unit_amount = int(Decimal(it.precio_unit) * 100)
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": it.titulo},
                "unit_amount": unit_amount,
            },
            "quantity": it.cantidad,
        })

    # Coste de envío como línea separada
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

    return render(request, "pedidos/checkout_tarjeta.html", {
        "session_id": session.id,
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
        "pedido": pedido,
    })


# ---------- Webhook Stripe ----------
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

            if pedido.pago_estado != "pagado":  # idempotencia básica
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

                # Email de confirmación
                try:
                    enviar_confirmacion_email(pedido)
                except Exception:
                    pass

    return HttpResponse(status=200)


# ---------- Paso final: OK ----------
def checkout_ok(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    # En tarjeta, vaciamos carrito cuando está pagado (el pedido se crea en checkout_tarjeta_pre)
    if pedido.pago_metodo == "tarjeta" and pedido.pago_estado == "pagado":
        try:
            Cart(request).clear()
        except Exception:
            pass
        for k in ("checkout_datos", "checkout_pago", "shipping_method_id"):
            request.session.pop(k, None)

    return render(request, "pedidos/checkout_ok.html", {"pedido": pedido})


# ---------- Seguimiento público por token ----------
def seguimiento(request, token):
    pedido = get_object_or_404(Pedido, tracking_token=token)
    return render(request, "pedidos/seguimiento.html", {"pedido": pedido})


# ---------- Seguimiento por ID + email (requisito literal) ----------
@require_http_methods(["GET", "POST"])
def seguimiento_id(request):
    pedido = None
    error = None
    if request.method == "POST":
        pid = (request.POST.get("id") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        if pid and email:
            pedido = Pedido.objects.filter(id=pid, email__iexact=email).first()
            if not pedido:
                error = "No se encontró un pedido con esos datos."
        else:
            error = "Indica el ID de pedido y tu email."
    return render(request, "pedidos/seguimiento_id.html", {"pedido": pedido, "error": error})


# ---------- Email de confirmación ----------
def enviar_confirmacion_email(pedido: Pedido):
    asunto = f"Confirmación de pedido #{pedido.id}"
    base = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
    tracking_url = f"{base}{reverse('pedidos:seguimiento', args=[pedido.tracking_token])}"
    cuerpo = (
        f"Gracias por su compra, {pedido.nombre}.\n\n"
        f"Importe: {pedido.total} €\n"
        f"Envío a: {pedido.direccion}, {pedido.cp} {pedido.ciudad}\n\n"
        f"Seguimiento: {tracking_url}\n"
    )
    try:
        send_mail(
            asunto,
            cuerpo,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
            [pedido.email],
        )
    except Exception:
        pass

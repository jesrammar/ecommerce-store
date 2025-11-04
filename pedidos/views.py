from __future__ import annotations
import stripe
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from .models import Pedido

from carrito.cart import Cart
from .models import ShippingMethod
from .services import (
    crear_pedido_desde_carrito,
    crear_pedido_tarjeta_pre,
    confirmar_pedido_tarjeta_exitoso,
)

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")

@require_http_methods(["GET", "POST"])
def checkout_datos(request):
    if request.method == "POST":
        campos = ["nombre","apellidos","email","telefono","direccion","ciudad","cp","provincia"]
        request.session["checkout_pago"] = {k: (request.POST.get(k) or "").strip() for k in campos}
        return redirect("pedidos:checkout_pago")
    return render(request, "pedidos/checkout_datos.html", {"datos": request.session.get("checkout_pago", {})})

@require_http_methods(["GET", "POST"])
def checkout_pago(request):
    datos = request.session.get("checkout_pago", {})
    if not datos:
        messages.info(request, "Introduce tus datos de envío antes de continuar.")
        return redirect("pedidos:checkout_datos")

    # Resumen carrito
    cart = Cart(request)
    subtotal = Decimal("0.00")
    for item in cart:
        price = Decimal(str(item.get("price") or item["product"].precio))
        qty = int(item.get("qty") or 0)
        subtotal += (price * qty)
    subtotal = subtotal.quantize(Decimal("0.01"))

    metodos = ShippingMethod.objects.filter(activo=True).order_by("orden", "nombre")
    seleccionado = request.session.get("shipping_method_id")

    ENVIO_GRATIS_DESDE = getattr(settings, "ENVIO_GRATIS_DESDE", Decimal("999999"))
    envio = Decimal("0.00")
    metodo_obj = None
    if seleccionado:
        metodo_obj = ShippingMethod.objects.filter(pk=seleccionado, activo=True).first()
    if subtotal < ENVIO_GRATIS_DESDE and metodo_obj:
        envio = Decimal(metodo_obj.coste or 0).quantize(Decimal("0.01"))
    total_preview = (subtotal + envio).quantize(Decimal("0.01"))

    if request.method == "GET":
        return render(
            request, "pedidos/checkout_pago.html",
            {
                "datos": datos,
                "metodos_envio": metodos,
                "seleccionado": int(seleccionado) if seleccionado else None,
                "subtotal": subtotal,
                "envio": envio,
                "total_preview": total_preview,
                "ENVIO_GRATIS_DESDE": ENVIO_GRATIS_DESDE,
            },
        )

    # POST -> contrareembolso
    try:
        pedido = crear_pedido_desde_carrito(request, {**datos, "pago_metodo": "contrareembolso"})
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("pedidos:checkout_pago")
    messages.success(request, "¡Pedido creado correctamente!")
    return redirect("pedidos:checkout_ok", pedido_id=getattr(pedido, "id", 0))

@require_POST
def seleccionar_envio(request):
    method_id = request.POST.get("shipping_method_id")
    if method_id and ShippingMethod.objects.filter(pk=method_id, activo=True).exists():
        request.session["shipping_method_id"] = int(method_id)
        request.session.modified = True
        messages.success(request, "Método de envío actualizado.")
    else:
        messages.error(request, "Método de envío no válido.")
    return redirect("pedidos:checkout_pago")

@require_http_methods(["GET", "POST"])
def checkout_tarjeta(request):
    datos = request.session.get("checkout_pago", {})
    if not datos:
        messages.info(request, "Introduce tus datos de envío antes de continuar.")
        return redirect("pedidos:checkout_datos")

    if request.method == "GET":
        return render(request, "pedidos/checkout_tarjeta.html",
                      {"datos": datos, "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY})

    try:
        pedido, totales = crear_pedido_tarjeta_pre(request, {**datos})
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    amount_cents = int((totales["total"] * 100).quantize(0))
    intent = stripe.PaymentIntent.create(
        amount=amount_cents, currency="eur",
        metadata={"pedido_id": str(pedido.id), "tracking_token": pedido.tracking_token},
    )
    if hasattr(pedido, "pago_ref"):
        pedido.pago_ref = intent.id
        pedido.save(update_fields=["pago_ref"])
    return JsonResponse({"client_secret": intent.client_secret, "pedido_id": pedido.id})

def checkout_ok(request, pedido_id: int):
    from .models import Pedido
    pedido = get_object_or_404(Pedido.objects.select_related("envio_metodo"), pk=pedido_id)
    return render(request, "pedidos/checkout_ok.html", {"pedido": pedido})

def seguimiento(request, token: str):
    from .models import Pedido
    pedido = get_object_or_404(
        Pedido.objects.select_related("envio_metodo").prefetch_related("items"),
        tracking_token=token,
    )
    return render(request, "pedidos/seguimiento.html", {"pedido": pedido})

@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if event["type"] == "payment_intent.succeeded":
        pi = event["data"]["object"]
        pedido_id = (pi.get("metadata") or {}).get("pedido_id")
        from .models import Pedido
        pedido = Pedido.objects.filter(pk=pedido_id).first() or Pedido.objects.filter(pago_ref=pi.get("id")).first()
        if pedido:
            confirmar_pedido_tarjeta_exitoso(pedido)
    return JsonResponse({"status": "ok"})


@login_required
def mis_pedidos(request):
    # Usamos el email del usuario logeado para encontrar sus pedidos
    user_email = request.user.email

    pedidos_qs = Pedido.objects.all()
    if user_email:
        pedidos_qs = pedidos_qs.filter(email__iexact=user_email)

    pedidos = pedidos_qs.order_by('-created_at')

    return render(request, "pedidos/mis_pedidos.html", {
        "pedidos": pedidos,
    })

@login_required
def pedido_detalle_usuario(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, cliente=request.user)
    return render(request, "pedidos/pedido_detalle_usuario.html", {"pedido": pedido})
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
from django.core.mail import send_mail
from django.urls import reverse

from .models import Pedido, ShippingMethod
from carrito.cart import Cart
from .services import (
    crear_pedido_desde_carrito,
    crear_pedido_tarjeta_pre,
    confirmar_pedido_tarjeta_exitoso,
)

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")


# ============================================================
#  Helper: envío de email de confirmación
# ============================================================

def _enviar_email_confirmacion(pedido: Pedido, request=None) -> None:
    """
    Envía un correo sencillo de confirmación de pedido al cliente.
    No lanza excepción si falla (fail_silently=True).
    """
    try:
        seguimiento_url = ""
        try:
            if request is not None:
                # construimos url absoluta de seguimiento si tenemos request
                seguimiento_url = request.build_absolute_uri(
                    reverse("pedidos:seguimiento", args=[pedido.tracking_token])
                )
            else:
                # si venimos de un contexto sin request (webhook), usamos SITE_URL
                base = getattr(settings, "SITE_URL", "").rstrip("/")
                if base:
                    seguimiento_url = f"{base}{reverse('pedidos:seguimiento', args=[pedido.tracking_token])}"
        except Exception:
            seguimiento_url = ""

        subject = f"Confirmación de pedido #{pedido.id}"
        lineas = [
            f"Hola {pedido.nombre},",
            "",
            "Gracias por tu compra en E-Clothify.",
            "",
            f"Número de pedido: {pedido.id}",
            f"Importe total: {pedido.total} €",
            f"Método de pago: {pedido.pago_metodo}",
        ]
        if seguimiento_url:
            lineas.append("")
            lineas.append(f"Puedes seguir el estado de tu pedido aquí: {seguimiento_url}")
        lineas.append("")
        lineas.append("Un saludo,")
        lineas.append("El equipo de E-Clothify")

        message = "\n".join(lineas)

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[pedido.email],
            fail_silently=True,  # no rompemos el flujo si falla el email
        )
    except Exception:
        # último seguro
        pass


# ============================================================
#  Checkout contrareembolso
# ============================================================

@require_http_methods(["GET", "POST"])
def checkout_datos(request):
    if request.method == "POST":
        campos = ["nombre", "apellidos", "email", "telefono",
                  "direccion", "ciudad", "cp", "provincia"]
        request.session["checkout_pago"] = {
            k: (request.POST.get(k) or "").strip()
            for k in campos
        }
        return redirect("pedidos:checkout_pago")

    return render(
        request,
        "pedidos/checkout_datos.html",
        {"datos": request.session.get("checkout_pago", {})},
    )


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
            request,
            "pedidos/checkout_pago.html",
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
        pedido = crear_pedido_desde_carrito(
            request,
            {**datos, "pago_metodo": "contrareembolso"},
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("pedidos:checkout_pago")

    # Enviamos correo de confirmación
    _enviar_email_confirmacion(pedido, request)

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


# ============================================================
#  Checkout tarjeta (Stripe)
# ============================================================

@require_http_methods(["GET", "POST"])
def checkout_tarjeta(request):
    datos = request.session.get("checkout_pago", {})
    if not datos:
        messages.info(request, "Introduce tus datos de envío antes de continuar.")
        return redirect("pedidos:checkout_datos")

    if request.method == "GET":
        return render(
            request,
            "pedidos/checkout_tarjeta.html",
            {"datos": datos, "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY},
        )

    try:
        pedido, totales = crear_pedido_tarjeta_pre(request, {**datos})
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    amount_cents = int((totales["total"] * 100).quantize(0))
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="eur",
        metadata={
            "pedido_id": str(pedido.id),
            "tracking_token": pedido.tracking_token,
        },
    )
    if hasattr(pedido, "pago_ref"):
        pedido.pago_ref = intent.id
        pedido.save(update_fields=["pago_ref"])

    return JsonResponse({"client_secret": intent.client_secret, "pedido_id": pedido.id})


def checkout_ok(request, pedido_id: int):
    pedido = get_object_or_404(
        Pedido.objects.select_related("envio_metodo"),
        pk=pedido_id,
    )
    return render(request, "pedidos/checkout_ok.html", {"pedido": pedido})


# ============================================================
#  Seguimiento por token (público)
# ============================================================

def seguimiento(request, token: str):
    pedido = get_object_or_404(
        Pedido.objects.select_related("envio_metodo").prefetch_related("items"),
        tracking_token=token,
    )
    return render(
        request,
        "pedidos/seguimiento.html",
        {"pedido": pedido, "desde_token": True},
    )


# ============================================================
#  Webhook Stripe
# ============================================================

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
        pedido = (
            Pedido.objects.filter(pk=pedido_id).first()
            or Pedido.objects.filter(pago_ref=pi.get("id")).first()
        )
        if pedido:
            confirmar_pedido_tarjeta_exitoso(pedido)
            # email de confirmación también en pago por tarjeta
            _enviar_email_confirmacion(pedido)

    return JsonResponse({"status": "ok"})


# ============================================================
#  Vistas de usuario: mis pedidos / detalle
# ============================================================

@login_required
def mis_pedidos(request):
    """
    Lista de pedidos del usuario logueado.

    Ahora utilizamos el campo Pedido.usuario, mucho más fiable que el email.
    """
    pedidos = (
        Pedido.objects
        .filter(usuario=request.user)
        .select_related("envio_metodo")
        .order_by("-created_at")
    )
    return render(request, "pedidos/mis_pedidos.html", {"pedidos": pedidos})


@login_required
def pedido_detalle_usuario(request, pk):
    """
    Detalle de un pedido perteneciente al usuario actual.
    Reutiliza la plantilla de seguimiento.
    """
    pedido = get_object_or_404(
        Pedido.objects.select_related("envio_metodo").prefetch_related("items"),
        pk=pk,
        usuario=request.user,
    )
    return render(
        request,
        "pedidos/seguimiento.html",
        {"pedido": pedido, "desde_mis_pedidos": True},
    )

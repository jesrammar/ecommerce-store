from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

from .forms import DatosEnvioForm, MetodoPagoForm
from .services import crear_pedido_desde_carrito
from .models import Pedido


# Paso 1: datos cliente + envío
def checkout_datos(request):
    if request.method == "POST":
        form = DatosEnvioForm(request.POST)
        if form.is_valid():
            request.session["checkout_datos"] = form.cleaned_data
            return redirect("pedidos:checkout_pago")
    else:
        form = DatosEnvioForm(initial=request.session.get("checkout_datos", {}))
    return render(request, "pedidos/checkout_datos.html", {"form": form})


# Paso 2: selección de método de pago
def checkout_pago(request):
    datos_cliente = request.session.get("checkout_datos")
    if not datos_cliente:
        messages.error(request, "Completa primero tus datos de entrega.")
        return redirect("pedidos:checkout_datos")

    if request.method == "POST":
        form = MetodoPagoForm(request.POST)
        if form.is_valid():
            request.session["checkout_pago"] = {
                "pago_metodo": form.cleaned_data["pago_metodo"]
            }
            request.session.modified = True

            if form.cleaned_data["pago_metodo"] == "contrareembolso":
                # Crear pedido directamente
                datos = {**datos_cliente, **request.session.get("checkout_pago", {})}
                pedido = crear_pedido_desde_carrito(request, datos)

                # limpiar datos de sesión de checkout
                request.session.pop("checkout_datos", None)
                request.session.pop("checkout_pago", None)

                return redirect("pedidos:checkout_ok", pedido_id=pedido.id)

            else:
                # Para tarjeta → pasaremos luego a Stripe
                return redirect("pedidos:checkout_tarjeta")
    else:
        initial = (request.session.get("checkout_pago") or {}).copy()
        form = MetodoPagoForm(initial=initial)

    return render(request, "pedidos/checkout_pago.html", {"form": form})


# Paso 3: confirmación
def checkout_ok(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, "pedidos/checkout_ok.html", {"pedido": pedido})


# Seguimiento por token público
def seguimiento(request, token):
    pedido = get_object_or_404(Pedido, tracking_token=token)
    return render(request, "pedidos/seguimiento.html", {"pedido": pedido})


# Envío de confirmación de pedido (puedes llamarlo desde services.py)
def enviar_confirmacion_email(pedido: Pedido):
    asunto = f"Confirmación de pedido #{pedido.id}"
    cuerpo = (
        f"Gracias por su compra, {pedido.nombre}.\n\n"
        f"Importe: {pedido.total} €\n"
        f"Envío a: {pedido.direccion}, {pedido.cp} {pedido.ciudad}\n\n"
        f"Seguimiento: {getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/seguimiento/{pedido.tracking_token}/\n"
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




def checkout_ok(request):
    from django.shortcuts import get_object_or_404
    from .models import Pedido
    pedido_id = request.GET.get("id")
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    return render(request, "pedidos/checkout_ok.html", {"pedido": pedido})

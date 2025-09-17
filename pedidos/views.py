from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import DatosEnvioForm
from .services import crear_pedido_desde_carrito
from .models import Pedido
from carrito.cart import Cart

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

# Paso 2: pago (simulado)
def checkout_pago(request):
    datos = request.session.get("checkout_datos")
    if not datos:
        return redirect("pedidos:checkout_datos")

    if request.method == "POST":
        try:
            pedido = crear_pedido_desde_carrito(request, datos)
            pedido.pago_estado = "pagado"
            pedido.pago_ref = "TEST-" + str(pedido.id)
            pedido.save(update_fields=["pago_estado", "pago_ref"])
            Cart(request).clear()
            enviar_confirmacion_email(pedido)
            request.session.pop("checkout_datos", None)
            return redirect("pedidos:checkout_ok", pedido_id=pedido.id)
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "pedidos/checkout_pago.html", {"datos": datos})

# Paso 3: confirmación
def checkout_ok(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, "pedidos/checkout_ok.html", {"pedido": pedido})

# Seguimiento por token
def seguimiento(request, token):
    pedido = get_object_or_404(Pedido, tracking_token=token)
    return render(request, "pedidos/seguimiento.html", {"pedido": pedido})

def enviar_confirmacion_email(pedido: Pedido):
    asunto = f"Confirmación de pedido #{pedido.id}"
    cuerpo = (
        f"Gracias por su compra, {pedido.nombre}.\n\n"
        f"Importe: {pedido.total} €\n"
        f"Envío a: {pedido.direccion}, {pedido.cp} {pedido.ciudad}\n\n"
        f"Seguimiento: {getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/seguimiento/{pedido.tracking_token}/\n"
    )
    try:
        send_mail(asunto, cuerpo, getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"), [pedido.email])
    except Exception:
        pass

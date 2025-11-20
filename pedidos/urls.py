from django.urls import path
from . import views

app_name = "pedidos"

urlpatterns = [
    path("checkout/datos/", views.checkout_datos, name="checkout_datos"),
    path("checkout/pago/", views.checkout_pago, name="checkout_pago"),
    path("checkout/tarjeta/", views.checkout_tarjeta, name="checkout_tarjeta"),
    path("checkout/ok/<int:pedido_id>/", views.checkout_ok, name="checkout_ok"),

    # Selección de envío (guarda en sesión)
    path("envio/seleccionar/", views.seleccionar_envio, name="seleccionar_envio"),

    # Seguimiento
    path("seguimiento/<str:token>/", views.seguimiento, name="seguimiento"),
    path("seguimiento-id/<int:pedido_id>/", views.seguimiento_por_id, name="seguimiento_id"),

    # Webhook Stripe
    path("webhooks/stripe/", views.stripe_webhook, name="stripe_webhook"),

    # Mis pedidos
    path("mis/", views.mis_pedidos, name="mis_pedidos"),
    path("mis/<int:pk>/", views.pedido_detalle_usuario, name="pedido_detalle_usuario"),
]

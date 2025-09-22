from django.urls import path
from . import views

app_name = "pedidos"

urlpatterns = [
    path("checkout/datos/", views.checkout_datos, name="checkout_datos"),
    path("checkout/pago/", views.checkout_pago, name="checkout_pago"),
    path("checkout/tarjeta/", views.checkout_tarjeta, name="checkout_tarjeta"),
    path("checkout/ok/<int:pedido_id>/", views.checkout_ok, name="checkout_ok"),

    # Seguimiento público por token
    path("seguimiento/<str:token>/", views.seguimiento, name="seguimiento"),

    # Seguimiento por ID+email (requisito literal)
    path("seguimiento-id/", views.seguimiento_id, name="seguimiento_id"),

    # Webhook de Stripe (CSRF exempt en la vista)
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]

from django.urls import path
from . import views

app_name = "pedidos"

urlpatterns = [
    path("checkout/datos/", views.checkout_datos, name="checkout_datos"),
    path("checkout/pago/", views.checkout_pago, name="checkout_pago"),
    path("checkout/tarjeta/", views.checkout_tarjeta, name="checkout_tarjeta"),
    path("checkout/ok/<int:pedido_id>/", views.checkout_ok, name="checkout_ok"),
    path("seguimiento/<str:token>/", views.seguimiento, name="seguimiento"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),

]

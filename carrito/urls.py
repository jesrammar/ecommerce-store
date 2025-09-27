from django.urls import path
from . import views

app_name = "carrito"

urlpatterns = [
    path("", views.carrito_ver, name="carrito_ver"),
    path("add/<int:product_id>/", views.carrito_add, name="carrito_add"),
    path("remove/<int:product_id>/", views.carrito_remove, name="carrito_remove"),
    path("update/<int:product_id>/", views.carrito_update, name="carrito_update"),
]

from django.urls import path
from . import views

app_name = "carrito"

urlpatterns = [
    path("", views.ver_carrito, name="carrito_ver"),
    path("add/<int:pid>/", views.add, name="carrito_add"),
    path("update/<int:pid>/", views.update, name="carrito_update"),
    path("remove/<int:pid>/", views.remove, name="carrito_remove"),
    path("clear/", views.clear, name="carrito_clear"),
    path("seleccionar-envio/", views.seleccionar_envio, name="seleccionar_envio"),

]

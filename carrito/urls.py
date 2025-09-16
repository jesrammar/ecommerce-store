from django.urls import path
from . import views

urlpatterns = [
    path("", views.ver_carrito, name="carrito_ver"),
    path("add/<int:pid>/", views.add, name="carrito_add"),
    path("remove/<int:pid>/", views.remove, name="carrito_remove"),
    path("update/<int:pid>/", views.update, name="carrito_update"),
    path("clear/", views.clear, name="carrito_clear"),
]

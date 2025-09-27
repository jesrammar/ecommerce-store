from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = "productos"

urlpatterns = [
    path("", views.lista_productos, name="catalogo"),
    path("c/<slug:slug>/", views.lista_por_categoria, name="catalogo_por_categoria"),
    path("p/<slug:slug>/", views.detalle_producto, name="producto_detalle"),
    path("p/<slug:slug>/preview/", views.preview_personalizacion, name="producto_preview"),
    path(
        "producto/<slug:slug>/",
        RedirectView.as_view(pattern_name="productos:producto_detalle", permanent=True),
        name="producto_detalle_legacy",
    ),
]

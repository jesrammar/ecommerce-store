from django.urls import path
from . import views

app_name = "productos"

urlpatterns = [
    path('', views.lista_productos, name='catalogo'),
    path('c/<slug:slug>/', views.lista_por_categoria, name='catalogo_por_categoria'),
    path('p/<slug:slug>/', views.detalle_producto, name='producto_detalle'),
    path('producto/<slug:slug>/', views.detalle_producto), 
    path('buscar/', views.buscar, name='buscar'),
]

from django.urls import path
from . import views

app_name = "gestion"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Productos
    path("productos/", views.admin_producto_list, name="admin_producto_list"),
    path("productos/nuevo/", views.admin_producto_create, name="admin_producto_create"),
    path("productos/<int:pk>/editar/", views.admin_producto_update, name="admin_producto_update"),
    path("productos/<int:pk>/eliminar/", views.admin_producto_delete, name="admin_producto_delete"),

    # Pedidos
    path("pedidos/", views.admin_pedido_list, name="admin_pedido_list"),
    path("pedidos/<int:pk>/", views.admin_pedido_detail, name="admin_pedido_detail"),
    path("pedidos/<int:pk>/cambiar-estado/", views.admin_pedido_update_estado, name="admin_pedido_update_estado"),
]

from django.contrib import admin
from django.urls import path, include
from productos.admin_views import (
    ProductoListView, ProductoCreateView, ProductoUpdateView, ProductoDeleteView
)
from django.conf import settings
from django.conf.urls.static import static
from pedidos import admin_views as pedidos_admin

urlpatterns = [
    path("", include(("productos.urls", "productos"), namespace="productos")),
    path("carrito/", include(("carrito.urls", "carrito"), namespace="carrito")),
    path("pedidos/", include(("pedidos.urls", "pedidos"), namespace="pedidos")),
    path("cuenta/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("django-admin/", admin.site.urls),

    # Backoffice simple
    path("gestion/productos/", ProductoListView.as_view(), name="admin_producto_list"),
    path("gestion/productos/nuevo/", ProductoCreateView.as_view(), name="admin_producto_create"),
    path("gestion/productos/<int:pk>/editar/", ProductoUpdateView.as_view(), name="admin_producto_update"),
    path("gestion/productos/<int:pk>/eliminar/", ProductoDeleteView.as_view(), name="admin_producto_delete"),

    path("gestion/pedidos/", pedidos_admin.pedidos_list, name="admin_pedido_list"),
    path("gestion/pedidos/<int:pk>/", pedidos_admin.pedido_detalle, name="admin_pedido_detail"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

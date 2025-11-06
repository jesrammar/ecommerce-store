# accounts/middleware.py
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import resolve_url, redirect
from django.urls import resolve


# Nombres completos "namespace:url_name" que serán públicos SIN login
# OJO: si algún nombre no coincide con tus urls, cámbialo aquí.
PUBLIC_ROUTE_NAMES = {
    # --- Auth ---
    "accounts:login",
    "accounts:registro",

    # --- Catálogo / escaparate ---
    # listado general
    "productos:catalogo",
    # listado filtrado por categoría (ajusta al nombre real si es distinto)
    "productos:catalogo_por_categoria",
    # detalle de producto
    "productos:producto_detalle",
    # si tienes vista de preview o detalle legacy, déjalas también públicas
    "productos:producto_preview",
    "productos:producto_detalle_legacy",

    # --- Carrito ---
    "carrito:carrito_ver",
    "carrito:carrito_add",
    "carrito:carrito_remove",
    "carrito:carrito_update",

    # --- Checkout (compra rápida sin registro) ---
    "pedidos:checkout_datos",
    "pedidos:checkout_pago",
    "pedidos:checkout_tarjeta",
    "pedidos:checkout_ok",
    "pedidos:seleccionar_envio",

    # --- Seguimiento de pedidos para invitados ---
    "pedidos:seguimiento",

    # --- Webhook de Stripe (lo llama Stripe, no el usuario) ---
    "pedidos:stripe_webhook",
}


class LoginRequiredMiddleware:
    """
    Fuerza autenticación en toda la web salvo rutas públicas.
    - Evita bucles de redirección.
    - Añade ?next=<ruta original> al login.
    - Permite /admin/, /django-admin/, /static/ y /media/.
    Coloca este middleware DESPUÉS de AuthenticationMiddleware en settings.MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info or "/"

        # 1) Dejar pasar admin/static/media
        if path.startswith(("/admin/", "/django-admin/", "/static/", "/media/")):
            return self.get_response(request)

        # 2) Resolver la ruta actual a nombre de vista
        try:
            match = resolve(path)
            if not match.url_name:
                # Rutas sin nombre (404, etc.) → no forzar login
                return self.get_response(request)
            full_name = f"{match.namespace}:{match.url_name}" if match.namespace else match.url_name
        except Exception:
            # Si no resuelve, no forzar (evita romper URLs ajenas)
            return self.get_response(request)

        # 3) Si ya está autenticado o es pública → continuar
        if request.user.is_authenticated or full_name in PUBLIC_ROUTE_NAMES:
            return self.get_response(request)

        # 4) Redirigir a LOGIN con ?next=<ruta original> (usa resolve_url por si es nombre)
        login_url = resolve_url(getattr(settings, "LOGIN_URL", "accounts:login"))
        next_value = request.get_full_path()  # incluye querystring original
        query = {"next": next_value}
        redirect_to = f"{login_url}?{urlencode(query)}"

        return redirect(redirect_to)

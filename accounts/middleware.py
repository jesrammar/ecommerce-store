# accounts/middleware.py
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import resolve_url, redirect
from django.urls import resolve


# Nombres completos "namespace:url_name" que serán públicos SIN login
# Si quieres que el seguimiento de pedidos sea público, añade: "pedidos:seguimiento"
PUBLIC_ROUTE_NAMES = {
    "accounts:login",
    "accounts:registro",
    # "pedidos:seguimiento",
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
        # usar la URL completa que el usuario pidió (incluye querystring original)
        next_value = request.get_full_path()
        query = {"next": next_value}
        redirect_to = f"{login_url}?{urlencode(query)}"

        return redirect(redirect_to)

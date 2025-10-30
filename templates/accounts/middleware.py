from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    """
    Fuerza el login en toda la web salvo las páginas públicas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs públicas permitidas sin login
        public_paths = [
            reverse('accounts:login'),
            reverse('accounts:registro'),
        ]

        # Si no está autenticado y no está en las páginas públicas → redirige al login
        if not request.user.is_authenticated and not any(request.path.startswith(p) for p in public_paths):
            return redirect('accounts:login')

        return self.get_response(request)

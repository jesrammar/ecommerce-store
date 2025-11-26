from pathlib import Path
import os
from decimal import Decimal
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-key")

# 👇 AHORA DEBUG SE LEE DEL .env
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

raw_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(",") if h.strip()]
print("### ALLOWED_HOSTS:", ALLOWED_HOSTS)


SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "productos",
    "carrito",
    "pedidos",
    "accounts.apps.AccountsConfig",
    "gestion",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "accounts.middleware.LoginRequiredMiddleware",
]

ROOT_URLCONF = "tienda_virtual.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "tienda_virtual.context_processors.globals",
            "carrito.context_processors.cart_summary",
        ],
    },
}]

WSGI_APPLICATION = "tienda_virtual.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Autenticación
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:after_login"
LOGOUT_REDIRECT_URL = "accounts:login"

LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static"   # tus archivos estáticos en desarrollo
]

STATIC_ROOT = BASE_DIR / "staticfiles"     # carpeta donde collectstatic guardará todo en producción


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 🚨 MUY IMPORTANTE: NADA DE IF DEBUG AQUÍ
# Email SIEMPRE por SMTP, cogiendo todo del .env
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
)

EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER or "noreply@example.com"
)

ENVIO_GRATIS_DESDE = Decimal("50.00")
MONEDA = "€"

STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

CSRF_TRUSTED_ORIGINS = [
    "https://ecommerce-store-65kd.onrender.com",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

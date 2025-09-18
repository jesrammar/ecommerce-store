from .settings import *  
import os

DEBUG = False

# Variables críticas desde el entorno
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if os.environ.get("DJANGO_ALLOWED_HOSTS") else []
CSRF_TRUSTED_ORIGINS = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS") else []

# Seguridad (HTTPS)
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# Detrás de proxy (Render/Koyeb/etc.)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Archivos estáticos en producción
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media (asegura volumen o servicio externo)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# Email real (ejemplo SMTP genérico)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.sendgrid.net")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@tu-dominio.es")

# URL pública del sitio para generar enlaces en emails
SITE_URL = os.environ.get("SITE_URL", "https://tu-dominio.es")

# Base de datos: usa la misma que en dev por defecto (SQLite),
# pero en PaaS deberías configurar Postgres y parsear la URL si aplica.
# Ejemplo (descomenta si usas DATABASE_URL):
# import dj_database_url
# DATABASES['default'] = dj_database_url.parse(os.environ.get("DATABASE_URL"), conn_max_age=600)

from pathlib import Path
import os
from decimal import Decimal
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000")

INSTALLED_APPS = [
    'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
    'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
    'productos','carrito','pedidos','accounts.apps.AccountsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
   
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
   'accounts.middleware.LoginRequiredMiddleware'
]

ROOT_URLCONF = 'tienda_virtual.urls'

TEMPLATES = [{
    'BACKEND':'django.template.backends.django.DjangoTemplates',
    'DIRS':[BASE_DIR/'templates'],
    'APP_DIRS':True,
    'OPTIONS':{
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'tienda_virtual.context_processors.globals',
            'carrito.context_processors.cart_summary',
       
        ],
    },
}]

WSGI_APPLICATION = 'tienda_virtual.wsgi.application'

DATABASES = {
    'default': {'ENGINE':'django.db.backends.sqlite3','NAME': BASE_DIR/'db.sqlite3'}
}

# Autenticación
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "/productos/"      # mejor mandar al catálogo tras login
LOGOUT_REDIRECT_URL = "accounts:login"      # y volver al login tras salir

LANGUAGE_CODE='es-es'
TIME_ZONE='Europe/Madrid'
USE_I18N=True
USE_TZ=True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']     # en dev
# STATIC_ROOT = BASE_DIR / 'staticfiles'     # en prod con collectstatic

MEDIA_URL='/media/'
MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'

EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL='noreply@example.com'

ENVIO_GRATIS_DESDE = Decimal("50.00")
MONEDA = "€"

STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

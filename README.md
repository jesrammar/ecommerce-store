# ecommerce-store

<p align="center">
  <img src="https://img.shields.io/badge/Django-4.2-111827?style=for-the-badge&logo=django&logoColor=0C4B33" alt="Django 4.2" />
  <img src="https://img.shields.io/badge/Python-3.12-111827?style=for-the-badge&logo=python&logoColor=3776AB" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Stripe-Test%20Mode-111827?style=for-the-badge&logo=stripe&logoColor=635BFF" alt="Stripe" />
  <img src="https://img.shields.io/badge/Status-Academic%20Project-111827?style=for-the-badge" alt="Academic Project" />
</p>

Proyecto de ecommerce construido con **Django**, orientado a cubrir el flujo completo de una tienda online: **catálogo**, **carrito**, **checkout**, **pagos**, **seguimiento de pedidos** y **panel de gestión** independiente del admin nativo de Django.

## Qué ofrece

- Catálogo con categorías, marcas y búsqueda.
- Carrito persistente por sesión.
- Checkout guiado en varios pasos.
- Pago con `Stripe` en modo test y opción de contrareembolso.
- Confirmación por email y seguimiento de pedidos.
- Panel de gestión propio para operación básica del negocio.

## Stack técnico

- `Python 3.12`
- `Django 4.2`
- `SQLite` para desarrollo
- `Stripe`
- `WhiteNoise` para estáticos
- `python-dotenv` para configuración por entorno

## Qué demuestra técnicamente

- Modelado de un flujo ecommerce end-to-end sobre Django.
- Gestión de sesión, autenticación y área privada de usuario.
- Integración con proveedor de pagos.
- Organización por apps (`productos`, `carrito`, `pedidos`, `accounts`, `gestion`).
- Separación entre experiencia de cliente y panel de gestión.

## Estructura funcional

- `productos`: catálogo, categorías, marcas y stock.
- `carrito`: carrito persistente y resumen de compra.
- `pedidos`: checkout, pedidos, seguimiento y pagos.
- `accounts`: login, registro y perfil.
- `gestion`: panel interno de gestión.

## Ejecutar en local

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Aplicación disponible en `http://127.0.0.1:8000`.

## Variables de entorno relevantes

Configura al menos:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `SITE_URL`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `STRIPE_PUBLIC_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

## Despliegue

El proyecto está preparado para separar configuración por entorno y servir estáticos con `WhiteNoise`. La configuración actual incluye valores para desarrollo local y ajustes pensados para despliegue web.

## Contexto

Este proyecto forma parte de mi portfolio como ejemplo de aplicación full-stack con Django. Aporta contexto de producto, pagos, gestión y experiencia de usuario, aunque mi foco profesional principal está hoy en **backend Java/Spring Boot**.

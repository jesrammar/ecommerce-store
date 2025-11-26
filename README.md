# 🧥 E-CLOTHIFY — Ecommerce Store (Django)

![Django](https://img.shields.io/badge/Django-4.2-0C4B33?logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-Test%20Mode-635BFF?logo=stripe&logoColor=white)
![Status](https://img.shields.io/badge/Status-Academic%20Project-0ea5e9)


Tienda online completa con catálogo, carrito, checkout, pagos (Stripe), envío, seguimiento y panel de gestión.

---
![demo](https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExaG9yczcxZ2h6b3A3dDRsMWZ6bTJwbjE2eW51bnFkdHQzcGNwaGQ5MSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/o0vwzuFwCGAFO/giphy.gif)

---

# 📑 Índice
1. [Descripción general](#-descripción-general)
2. [Requisitos del producto](#-requisitos-del-producto)
3. [Requisitos del proyecto](#-requisitos-del-proyecto)
4. [Modelo de datos](#-modelo-de-datos)
5. [Mapa de navegación](#-mapa-de-navegación)
6. [Tecnologías utilizadas](#-tecnologías-utilizadas)
7. [Instalación y ejecución](#️-instalación-y-ejecución)
8. [Variables de entorno](#-variables-de-entorno)
9. [Pagos con Stripe](#-pagos-con-stripe)
10. [Estructura del proyecto](#-estructura-del-proyecto)
11. [Notas de despliegue (Render)](#-notas-de-despliegue-render)
12. [Equipo de trabajo](#-equipo-de-trabajo)
13. [Licencia](#-licencia)

---

# 📌 Descripción general

E-CLOTHIFY es un ecommerce B2C construido con **Django**, ofreciendo:

- Catálogo navegable con filtros  
- Carrito persistente por sesión  
- Checkout en ≤ 3 pasos  
- Envío + pago (contrareembolso o tarjeta, Stripe)  
- Confirmación por email  
- Seguimiento por token o por ID  
- Panel de gestión **independiente del admin de Django**

Optimizado para despliegue en **Render**.

---

# ✅ Requisitos del producto

### 🛒 Catálogo
- Categorías, marcas y búsqueda por texto.
- Control de stock (agotado).
- Imagen principal de producto.

### 🌐 Carrito
- Cantidades (+/−).
- Totales dinámicos.
- Persistencia en sesión.

### 💳 Checkout
- 3 pasos: datos → pago → confirmación.
- Permite invitado.
- Validación de stock y envío.

### 📦 Pedidos y seguimiento
- Email de confirmación.
- Seguimiento:
  - Token único
  - ID + email

### 🔐 Autenticación
- Email + contraseña.
- Perfil editable.

### ⚙️ Panel de gestión
- Métricas (productos, pedidos, pendientes).
- Cambios rápidos de estado.
- Vista detallada.
- Interfaz visual moderna.

---

# 📋 Requisitos del proyecto

### Cliente
- Pruebas en PaaS (Render).
- Entrega con documentación.

### Organización
- Metodología híbrida.
- Requisitos: Django, VS Code, Stripe.
- Admin de Django solo en desarrollo.

---

# 🗄️ Modelo de datos

Entidades principales:

- `Producto`
- `Categoria`
- `Marca`
- `Pedido`
- `PedidoItem`
- `ShippingMethod`
- `User` (Django)
- Carrito → almacenado en **sesión**

---

# 🧭 Mapa de navegación


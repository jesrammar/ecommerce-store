# 🛒 Ecommerce Store (Django)

Proyecto académico de **Planificación y Gestión de Proyectos Informáticos**.  
Solución **B2C** con **Django** que permite una experiencia de compra completa: catálogo, carrito, checkout, envío, pagos (contrareembolso y tarjeta con Stripe), y seguimiento de pedidos.

---

## 📑 Índice
- [Descripción del proyecto](#descripción-del-proyecto)
- [Requisitos del producto](#requisitos-del-producto)
- [Requisitos del proyecto](#requisitos-del-proyecto)
- [Modelo de datos](#modelo-de-datos)
- [Mapa de navegación](#mapa-de-navegación)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Variables de entorno](#variables-de-entorno)
- [Pagos](#pagos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Notas de despliegue](#notas-de-despliegue)
- [Equipo de trabajo](#equipo-de-trabajo)
- [Licencia](#licencia)

---

## 📌 Descripción del proyecto
La empresa cliente (distribución de bienes) busca dar el salto al e-commerce. Se entrega una tienda **B2C** funcional desplegable en **PaaS**, con backoffice mínimo para gestión de pedidos.

---

## ✅ Requisitos del producto
- Cesta de compra visible con control de cantidades (+/−).
- Catálogo por **categorías** (y **marca**).
- Checkout ≤ **3 pasos** (datos → pago → confirmación), admite invitado.
- Login por **email + contraseña**.
- **Español**, sensación de compra segura.
- **Seguimiento** por token (y por **ID + email**).
- Productos **agotados** marcados y no añadibles.
- Una **imagen principal** por producto.
- **Búsqueda** por nombre, categoría y marca (desde inicio).
- Email de **confirmación de pedido**.
- No se contemplan devoluciones.
- **Marca corporativa** reflejada.
- Administración fuera del admin de Django (mínimo: pedidos).

---

## 📋 Requisitos del proyecto
**Cliente**
- Versiones de pruebas en **PaaS**.
- Entrega de **código** + **instrucciones**.

**Organización**
- Ciclo de vida **híbrido**.
- Plantillas oficiales.
- Tecnologías: **Django** + **VS Code**.
- **Django admin** solo en desarrollo.

---

## 🗄️ Modelo de datos
Entidades implementadas:
- `Producto`, `Categoria`, `Marca`
- `Pedido`, `PedidoItem`, `ShippingMethod`
- `User` (Django) para clientes
- Carrito en **sesión** (no DB)

> Diagramas incluidos en `/docs` (si aplican).

---

## 🧭 Mapa de navegación
Inicio → Catálogo → Ficha → Carrito → **Seleccionar envío** → Checkout (Datos) → Pago (Contrareembolso / Tarjeta) → **Confirmación** → **Seguimiento**.

---

## 🛠️ Tecnologías utilizadas
- **Python 3.12**, **Django 4.2**
- **Bootstrap 5**
- **Stripe** (pagos tarjeta)
- **SQLite** (dev) / **PostgreSQL** (prod opcional)
- PaaS: Render / Koyeb / PythonAnywhere

---

## ⚙️ Instalación y ejecución

### 1) Clonar
```bash
git clone https://github.com/jesrammar/ecommerce-store.git
cd ecommerce-store

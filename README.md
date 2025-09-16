# 🛒 Ecommerce Store (Django)

Proyecto académico de **Planificación y Gestión de Proyectos Informáticos** (Universidad), desarrollado con **Django** como framework principal.  
El objetivo es implementar una **tienda online B2C** completa que permita a los clientes realizar compras de forma rápida, segura y sencilla.

---

## 📑 Índice
- [Descripción del proyecto](#descripción-del-proyecto)
- [Requisitos del producto](#requisitos-del-producto)
- [Requisitos del proyecto](#requisitos-del-proyecto)
- [Modelo de datos](#modelo-de-datos)
- [Mapa de navegación](#mapa-de-navegación)
- [Tecnologías utilizadas](#tecnologías-utilizadas)
- [Instalación y ejecución](#instalación-y-ejecución)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Equipo de trabajo](#equipo-de-trabajo)
- [Licencia](#licencia)

---

## 📌 Descripción del proyecto
La empresa cliente, dedicada a la distribución de bienes, busca dar el salto al comercio electrónico.  
La **empresa consultora** (simulada en la práctica) nos encarga el desarrollo de una solución B2C de e-commerce, en la que:

- El **grupo de prácticas** actúa como **equipo director** y **equipo de desarrollo**.
- El **profesor** asume el rol de **patrocinador**.
- Se entrega un **producto software funcional** desplegado en un **PaaS**.

---

## ✅ Requisitos del producto
- Cesta de compra siempre visible, con control de cantidades (+/−).
- Catálogo organizado por categorías idénticas a las tiendas físicas.
- Proceso de compra rápido (≤ 3 pasos), incluso sin registro.
- Identificación de usuario por **correo y contraseña**.
- Compra segura, idioma de la tienda en **Español**.
- Seguimiento de pedido incluso para clientes invitados.
- Productos agotados claramente indicados.
- Cada producto con **una sola imagen principal**.
- Búsqueda por nombre, categoría o fabricante, disponible desde la página de inicio.
- Flujo de checkout: datos cliente → datos envío → datos pago.
- Confirmación por correo con detalles de pedido y envío.
- No se contemplan devoluciones.
- La web refleja la **marca corporativa** del cliente.
- Administración de contenidos propia (no Django admin en producción).

---

## 📋 Requisitos del proyecto
### Cliente
- Versiones para pruebas disponibles en un **PaaS**.
- Entrega del código fuente + instrucciones de instalación y despliegue.

### Organización (consultora)
- Ciclo de vida **híbrido**.
- Uso de **plantillas oficiales** de la organización.
- Herramientas: **Django** y **Visual Studio Code**.
- Django Admin solo para desarrollo.

---

## 🗄️ Modelo de datos
Basado en el análisis proporcionado:

**Entidades principales:**
- **Producto**: nombre, descripción, precio, stock, disponible, destacado, etc.
- **Categoria**: nombre, descripción, imagen.
- **Marca**: nombre, imagen.
- **Cliente**: datos personales, email, dirección, contraseña.
- **Carrito** + `ItemCarrito`.
- **Pedido** + `ItemPedido`.
- **ImagenProducto** (principal/secundarias).
- **TallaProducto** (si aplica).

📎 Ver detalle completo en [`Modelo de Datos.pdf`](./docs/Modelo%20de%20Datos.pdf):contentReference[oaicite:0]{index=0}.

---

## 🧭 Mapa de navegación
- **Inicio**
  - Catálogo / Categorías / Contacto / Acerca de
- **Página de producto individual**
- **Carrito de compra**
- **Checkout**
  - Identificación
  - Registro (opcional)
  - Detalles de entrega
  - Detalles de pago
  - Confirmación de compra

📎 Ver esquema gráfico en [`navigation_site_map.pdf`](./docs/navigation_site_map.pdf):contentReference[oaicite:1]{index=1}.

---

## 🛠️ Tecnologías utilizadas
- **Python 3.12**
- **Django 4.x**
- **SQLite / PostgreSQL** (según despliegue)
- **Bootstrap 5** (con `django-bootstrap-v5`)
- **Visual Studio Code**
- **GitHub + repositorios remotos (uni/personal)**
- Despliegue en **Render / Koyeb / PythonAnywhere (PaaS)**

---

## ⚙️ Instalación y ejecución
1. Clonar el repositorio:
   ```bash
   git clone https://github.com/jesrammar/ecommerce-store.git
   cd ecommerce-store

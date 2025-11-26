from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import FieldError
from django.shortcuts import get_object_or_404, redirect, render

from productos.models import Producto
from pedidos.models import Pedido
from .forms import ProductoForm



@staff_member_required(login_url="accounts:login")
def dashboard(request):
    """
    Dashboard básico y robusto.
    Si algo raro pasa con Pedido, no rompe la página.
    """
    # Productos
    try:
        productos_total = Producto.objects.count()
    except Exception:
        productos_total = 0

    # Pedidos totales
    try:
        pedidos_total = Pedido.objects.count()
    except Exception:
        pedidos_total = 0

    # Pendientes
    try:
        pedidos_pendientes = Pedido.objects.filter(
            estado__in=["pendiente", "PENDIENTE"]
        ).count()
    except Exception:
        pedidos_pendientes = 0

    # Últimos pedidos (solo id)
    try:
        pedidos_ultimos = list(Pedido.objects.order_by("-id")[:10])
    except Exception:
        pedidos_ultimos = []

    ctx = {
        "productos_total": productos_total,
        "pedidos_total": pedidos_total,
        "pedidos_pendientes": pedidos_pendientes,
        "pedidos_ultimos": pedidos_ultimos,
    }
    return render(request, "gestion/dashboard.html", ctx)



@staff_member_required(login_url="accounts:login")
def admin_producto_list(request):
    qs = Producto.objects.order_by("-id")
    return render(request, "gestion/producto_list.html", {"productos": qs})


@staff_member_required(login_url="accounts:login")
def admin_producto_create(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto creado correctamente.")
            return redirect("gestion:admin_producto_list")
    else:
        form = ProductoForm()
    return render(request, "gestion/producto_form.html", {"form": form, "modo": "crear"})


@staff_member_required(login_url="accounts:login")
def admin_producto_update(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado.")
            return redirect("gestion:admin_producto_list")
    else:
        form = ProductoForm(instance=producto)
    return render(
        request,
        "gestion/producto_form.html",
        {"form": form, "modo": "editar", "producto": producto},
    )


@staff_member_required(login_url="accounts:login")
def admin_producto_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        producto.delete()
        messages.success(request, "Producto eliminado.")
        return redirect("gestion:admin_producto_list")
    return render(request, "gestion/producto_confirm_delete.html", {"producto": producto})



@staff_member_required(login_url="accounts:login")
def admin_pedido_list(request):
    """
    Lista de pedidos ULTRA robusta:
    - Cargamos los pedidos
    - Construimos una lista de diccionarios "seguros"
    - Si algo falla, mostramos mensaje y no rompemos.
    """
    safe_pedidos = []

    try:
        qs = Pedido.objects.all().order_by("-id")
        for p in qs:
            try:
              
                pid = getattr(p, "id", None)
                fecha = getattr(
                    p,
                    "fecha",
                    getattr(p, "created_at", getattr(p, "creado", None)),
                )
                cliente = getattr(
                    p,
                    "usuario",
                    getattr(p, "user", getattr(p, "cliente", None)),
                )
                estado = getattr(p, "estado", "")

                safe_pedidos.append(
                    {
                        "id": pid,
                        "fecha": fecha,
                        "cliente": cliente,
                        "estado": estado,
                    }
                )
            except Exception as e:
              
                messages.warning(
                    request, f"Pedido con problemas al mostrarlo (ID desconocido): {e}"
                )
    except Exception as e:
        messages.error(request, f"Error cargando pedidos: {e}")

    return render(request, "gestion/pedidos_list.html", {"pedidos": safe_pedidos})


@staff_member_required(login_url="accounts:login")
def admin_pedido_detail(request, pk):
    """
    Vista de detalle de pedido para el panel de gestión.
    Muestra datos del pedido + líneas de pedido y permite cambiar el estado.
    """
    pedido = get_object_or_404(Pedido, pk=pk)


    items = pedido.items.all()

  
    estados_sugeridos = ["pendiente", "aceptado", "enviado", "cancelado", "completado"]

    contexto = {
        "pedido": pedido,
        "items": items,
        "estados_sugeridos": estados_sugeridos,
    }
    return render(request, "gestion/pedido_detail.html", contexto)

@staff_member_required(login_url="accounts:login")
def admin_pedido_update_estado(request, pk):
    """
    Cambia el estado del pedido:
    - Desde la lista: botón 'Aceptar' (estado=aceptado)
    - Desde el detalle: select de estados
    ¡Siempre sin tirar 500!
    """
    try:
        pedido = Pedido.objects.get(pk=pk)
    except Pedido.DoesNotExist:
        messages.error(request, "El pedido no existe.")
        return redirect("gestion:admin_pedido_list")
    except Exception as e:
        messages.error(request, f"Error cargando el pedido: {e}")
        return redirect("gestion:admin_pedido_list")

    if request.method == "POST":
        nuevo_estado = (request.POST.get("estado") or "").strip()

        if not nuevo_estado:
            messages.error(request, "Debes indicar un estado válido.")
        else:
            try:
                field_names = [f.name for f in Pedido._meta.get_fields()]
                if "estado" in field_names:
                    pedido.estado = nuevo_estado
                    try:
                        pedido.save(update_fields=["estado"])
                    except Exception:
                        pedido.save()
                    messages.success(
                        request,
                        f"Estado del pedido #{pedido.id} actualizado a '{nuevo_estado}'.",
                    )
                else:
                    messages.error(
                        request,
                        "Este modelo de Pedido no tiene el campo 'estado'. "
                        "Si usas otro nombre (p.ej. 'status'), adapta la vista.",
                    )
            except FieldError:
                messages.error(
                    request, "No es posible cambiar el estado: el campo no existe."
                )
            except Exception as e:
                messages.error(request, f"Error al actualizar el estado: {e}")

    next_url = request.POST.get("next") or ""
    if next_url:
        return redirect(next_url)
    return redirect("gestion:admin_pedido_detail", pk=pk)

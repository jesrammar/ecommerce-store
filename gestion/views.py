from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import FieldError
from django.shortcuts import get_object_or_404, redirect, render

from productos.models import Producto
from pedidos.models import Pedido
from .forms import ProductoForm


# ---------- Dashboard ----------
@staff_member_required(login_url="accounts:login")
def dashboard(request):
    """
    Dashboard robusto: no asume que 'Pedido' tenga campo 'estado'.
    Si no existe, no rompe (cuenta pendientes = 0).
    """
    productos_total = Producto.objects.count()
    pedidos_total = Pedido.objects.count()

    # Algunos esquemas no tienen 'estado' o lo llaman distinto → evitar FieldError
    try:
        pedidos_pendientes = Pedido.objects.filter(estado__in=["pendiente", "PENDIENTE"]).count()
    except FieldError:
        pedidos_pendientes = 0

    pedidos_ultimos = Pedido.objects.order_by("-id")[:10]

    ctx = {
        "productos_total": productos_total,
        "pedidos_total": pedidos_total,
        "pedidos_pendientes": pedidos_pendientes,
        "pedidos_ultimos": pedidos_ultimos,
    }
    return render(request, "gestion/dashboard.html", ctx)


# ---------- Productos (CRUD) ----------
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


# ---------- Pedidos ----------
@staff_member_required(login_url="accounts:login")
def admin_pedido_list(request):
    pedidos = Pedido.objects.order_by("-id")
    return render(request, "gestion/pedidos_list.html", {"pedidos": pedidos})


@staff_member_required(login_url="accounts:login")
def admin_pedido_detail(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    return render(request, "gestion/pedido_detail.html", {"pedido": pedido})


@staff_member_required(login_url="accounts:login")
def admin_pedido_update_estado(request, pk):
    """
    Cambia el estado del pedido (si el modelo lo tiene).
    Si no existe el campo, muestra error de usuario pero no rompe.
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        nuevo_estado = (request.POST.get("estado") or "").strip()
        try:
            if nuevo_estado:
                # Solo intentamos si existe el campo:
                if "estado" in [f.name for f in Pedido._meta.get_fields()]:
                    pedido.estado = nuevo_estado
                    pedido.save(update_fields=["estado"])
                    messages.success(request, "Estado del pedido actualizado.")
                else:
                    messages.error(request, "Este modelo de Pedido no tiene el campo 'estado'.")
            else:
                messages.error(request, "Debes indicar un estado válido.")
        except FieldError:
            messages.error(request, "No es posible cambiar el estado: el campo no existe.")
    return redirect("gestion:admin_pedido_detail", pk=pk)

from django.contrib.auth.decorators import user_passes_test, login_required
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Producto

def staff_required(u):
    return u.is_active and u.is_staff

class StaffRequiredMixin:
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        return login_required(user_passes_test(staff_required)(view))

class ProductoListView(StaffRequiredMixin, ListView):
    model = Producto
    template_name = "admin/producto_list.html"
    paginate_by = 20
    queryset = Producto.objects.select_related("categoria", "marca").order_by("-creado")

class ProductoCreateView(StaffRequiredMixin, CreateView):
    model = Producto
    fields = [
        "nombre",
        "slug",
        "descripcion",
        "precio",
        "precio_oferta",
        "imagen",
        "marca",
        "categoria",
        "color",
        "es_destacado",
        "activo",
    ]
    template_name = "admin/producto_form.html"
    success_url = reverse_lazy("admin_producto_list")

class ProductoUpdateView(StaffRequiredMixin, UpdateView):
    model = Producto
    fields = [
        "nombre",
        "slug",
        "descripcion",
        "precio",
        "precio_oferta",
        "imagen",
        "marca",
        "categoria",
        "color",
        "es_destacado",
        "activo",
    ]
    template_name = "admin/producto_form.html"
    success_url = reverse_lazy("admin_producto_list")

class ProductoDeleteView(StaffRequiredMixin, DeleteView):
    model = Producto
    template_name = "admin/producto_confirm_delete.html"
    success_url = reverse_lazy("admin_producto_list")

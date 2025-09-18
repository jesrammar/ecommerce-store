from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from .models import Producto, Categoria

def lista_productos(request):
    q = request.GET.get("q", "")
    productos = Producto.objects.filter(activo=True)
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
    categorias = Categoria.objects.all().order_by("nombre")
    return render(request, "productos/lista.html", {"productos": productos, "categorias": categorias, "q": q})

def lista_por_categoria(request, slug):
    categoria = get_object_or_404(Categoria, slug=slug)
    productos = categoria.productos.filter(activo=True)
    categorias = Categoria.objects.all().order_by("nombre")
    return render(request, "productos/lista.html", {"productos": productos, "categorias": categorias, "categoria": categoria})

def detalle_producto(request, slug):
    p = get_object_or_404(Producto, slug=slug, activo=True)
    return render(request, "productos/detalle.html", {"producto": p})

def buscar(request):
    return lista_productos(request)

from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from .models import Producto, Categoria, Marca

def lista_productos(request):
    q = request.GET.get("q", "").strip()
    categoria_slug = request.GET.get("categoria", "").strip()
    marca_slug = request.GET.get("marca", "").strip()

    productos = Producto.objects.filter(activo=True)

    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))
    if categoria_slug:
        productos = productos.filter(categoria__slug=categoria_slug)
    if marca_slug:
        productos = productos.filter(marca__slug=marca_slug)

    ctx = {
        "q": q,
        "categoria_sel": categoria_slug,
        "marca_sel": marca_slug,
        "categorias": Categoria.objects.order_by("nombre"),
        "marcas": Marca.objects.order_by("nombre"),
        "productos": productos.select_related("categoria", "marca"),
    }
    return render(request, "productos/lista.html", ctx)
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

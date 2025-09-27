from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from .models import Producto, Categoria, Marca, Variante
from .forms import VarianteForm, PersonalizacionForm

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
    return render(request, "productos/lista.html",
                  {"productos": productos, "categorias": categorias, "categoria": categoria})

def detalle_producto(request, slug):
    producto = get_object_or_404(Producto, slug=slug, activo=True)

    variantes = producto.variantes.all()
    tallas = variantes.values_list("talla", flat=True).distinct()
    colores = variantes.values_list("color", flat=True).distinct()

    var_form = VarianteForm(producto=producto)
    pers_form = PersonalizacionForm()

    ctx = {
        "producto": producto,
        "variantes": variantes,
        "tallas": tallas,
        "colores": colores,
        "var_form": var_form,
        "pers_form": pers_form,
    }
    return render(request, "productos/detalle.html", ctx)

def _generar_mockup(base_path, texto=None, color="#ffffff", img_overlay_path=None):
    base = Image.open(base_path).convert("RGBA")
    if img_overlay_path:
        overlay = Image.open(img_overlay_path).convert("RGBA")
        overlay.thumbnail((500, 500))
        base.alpha_composite(overlay, (180, 220))
    if texto:
        draw = ImageDraw.Draw(base)
        try:
            
          
            font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        draw.text((200, 120), texto, font=font, fill=color)

    buf = BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    filename = f"personalizados/mockup_{uuid4().hex}.png"
    path = default_storage.save(filename, ContentFile(buf.read()))
    return default_storage.url(path)

from django.views.decorators.http import require_POST
def _save_tmp_upload(fieldfile):
    tmp_name = f"personalizados/uploads/{uuid4().hex}_{fieldfile.name}"
    saved = default_storage.save(tmp_name, fieldfile)
    return default_storage.path(saved)

@require_POST
def preview_personalizacion(request, slug):
    producto = get_object_or_404(Producto, slug=slug, activo=True)
    if not producto.permite_personalizacion:
        return HttpResponseBadRequest("Este producto no permite personalización")

    form = PersonalizacionForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest("Datos inválidos")

    texto = form.cleaned_data.get("texto") or ""
    color = form.cleaned_data.get("color_texto") or "#ffffff"
    imagen = form.cleaned_data.get("imagen")

    if not producto.imagen:
        return HttpResponseBadRequest("Producto sin imagen base")

    img_path = _save_tmp_upload(imagen) if imagen else None
    preview_url = _generar_mockup(producto.imagen.path, texto=texto, color=color, img_overlay_path=img_path)
    return JsonResponse({"preview_url": preview_url})

def detalle_producto(request, slug):
    p = get_object_or_404(Producto, slug=slug, activo=True)
    qs_var = getattr(p, "variantes", None)
    tallas = colores = variantes = []
    if qs_var:
        variantes = list(qs_var.all())
        tallas   = sorted({v.talla for v in variantes if v.talla})
        colores  = sorted({v.color for v in variantes if v.color})

    return render(request, "productos/detalle.html", {
        "producto": p,
        "tallas": tallas,
        "colores": colores,
        "variantes": variantes,
    })


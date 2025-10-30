from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.contrib.messages import get_messages
from django.contrib import messages as dj_messages

from .forms import RegistroForm, PerfilForm, AddressForm
from .models import Address




def _norm(val):
    """Convierte 'None', 'null', '' en None; deja el resto igual (str o nombre de url)."""
    if val is None:
        return None
    s = str(val).strip()
    return None if s == "" or s.lower() in {"none", "null"} else s


def _safe_next(request):
    nxt = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return None


def _fallback_url(default_name="productos:catalogo"):
    """
    Fallback robusto para redirecciones después de login/logout.
    Usa settings.LOGIN_REDIRECT_URL o settings.LOGOUT_REDIRECT_URL si existen
    y, si no, cae al nombre de URL indicado.
    """
    return default_name


def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            # 🔐 loguear automáticamente
            login(request, user)
            messages.success(request, "¡Registro completado! Bienvenido.")

            # ir a 'next' si venía, o al catálogo
            target = request.POST.get("next") or getattr(settings, "LOGIN_REDIRECT_URL", None) or "productos:catalogo"
            return redirect(resolve_url(target))
    else:
        form = RegistroForm()
    return render(request, "accounts/registro.html", {"form": form})





def login_view(request):
    nxt = _norm(request.POST.get("next") or request.GET.get("next"))
    # coge el de settings si existe, pero normalizado también
    setting_target = _norm(getattr(settings, "LOGIN_REDIRECT_URL", None))
    target = nxt or setting_target or "/productos/"  # ruta segura por defecto

    if request.user.is_authenticated:
        return redirect(target)

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Has iniciado sesión.")
            return redirect(target)   # <-- NO resolve_url: redirect acepta rutas o nombres
        messages.error(request, "Credenciales inválidas.")
    return render(request, "accounts/login.html", {"next": nxt})



@login_required
def perfil(request):
    perfil = request.user.profile
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado.")
            return redirect("accounts:perfil")
    else:
        form = PerfilForm(instance=perfil)
    direcciones = request.user.addresses.all().order_by("-es_predeterminada", "id")
    return render(request, "accounts/perfil.html", {"form": form, "direcciones": direcciones})


@login_required
def address_create(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            addr.save()
            if not request.user.addresses.filter(es_predeterminada=True).exists():
                addr.es_predeterminada = True
                addr.save()
                request.user.profile.direccion_envio_pred = addr
                request.user.profile.save()
            messages.success(request, "Dirección añadida.")
            return redirect("accounts:perfil")
    else:
        form = AddressForm()
    return render(request, "accounts/address_form.html", {"form": form})


@login_required
def address_edit(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        form = AddressForm(request.POST, instance=addr)
        if form.is_valid():
            form.save()
            messages.success(request, "Dirección actualizada.")
            return redirect("accounts:perfil")
    else:
        form = AddressForm(instance=addr)
    return render(request, "accounts/address_form.html", {"form": form})


@login_required
def address_delete(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == "POST":
        addr.delete()
        messages.success(request, "Dirección eliminada.")
        return redirect("accounts:perfil")
    return render(request, "accounts/address_confirm_delete.html", {"addr": addr})


@login_required
def address_make_default(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    request.user.addresses.update(es_predeterminada=False)
    addr.es_predeterminada = True
    addr.save()
    request.user.profile.direccion_envio_pred = addr
    request.user.profile.save()
    messages.success(request, "Dirección establecida como predeterminada.")
    return redirect("accounts:perfil")


def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión.")   # ← solo aquí
    return redirect(resolve_url(getattr(settings, "LOGOUT_REDIRECT_URL", "accounts:login")))

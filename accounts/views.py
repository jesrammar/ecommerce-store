from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import RegistroForm, PerfilForm, AddressForm
from .models import Address

def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            messages.success(request, "Registro completado. Ya puedes iniciar sesión.")
            return redirect("accounts:login")
    else:
        form = RegistroForm()
    return render(request, "accounts/registro.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Has iniciado sesión.")
            next_url = request.GET.get("next") or reverse("home")
            return redirect(next_url)
        messages.error(request, "Credenciales inválidas.")
    return render(request, "accounts/login.html")

def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión.")
    return redirect("home")

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
